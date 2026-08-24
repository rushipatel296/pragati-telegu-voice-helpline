import os
import uuid
import json
import logging
import urllib.parse
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import uvicorn

# SQLAlchemy Dependencies
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import UserSessionModel

# Initialize database tables
Base.metadata.create_all(bind=engine)

import chromadb
from chromadb.utils import embedding_functions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] | %(name)s | %(message)s"
)
logger = logging.getLogger("PRAGATI_BOT")

load_dotenv()
client = OpenAI()

app = FastAPI(title="PRAGATI Helpline Voice Bot")

class IntentRequest(BaseModel):
    session_id: str
    user_text: str



# =====================================================================
# RAG: VECTOR DATABASE SETUP
# =====================================================================
try:
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"
    )
    # Load the collection we created in ingest_schemes.py
    schemes_collection = chroma_client.get_collection(
        name="telangana_schemes", 
        embedding_function=openai_ef # type: ignore
    )
    logger.info("✅ ChromaDB connected successfully.")
except Exception as e:
    logger.warning(f"⚠️ ChromaDB connection failed. Did you run ingest_schemes.py? Error: {e}")

    
# =====================================================================
# SERVICE LAYER (Refactored with Database)
# =====================================================================

async def transcribe_service(audio_file: UploadFile) -> str:
    """Handles Audio -> Telugu Text conversion"""
    if not audio_file.filename:
        logger.warning("Transcription attempt failed: No audio file provided.")
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    logger.info(f"[Whisper ASR] Starting transcription for file: '{audio_file.filename}' (Type: {audio_file.content_type})")
    
    try:
        file_bytes = await audio_file.read()
        audio_tuple = (audio_file.filename, file_bytes, audio_file.content_type)
        
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_tuple,
            prompt="నమస్కారం, దయచేసి నేను చెప్పేది వినండి. ఇది తెలంగాణ ప్రభుత్వ పథకాలకు సంబంధించినది."
        )
        
        logger.info(f"[Whisper ASR] Success | Transcribed Text: \"{response.text}\"")
        return response.text

    except Exception as e:
        logger.error(f"[Whisper ASR] Error transcribing file '{audio_file.filename}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


async def process_intent_service(session_id: str, user_text: str, db: Session) -> dict:
    """Handles User Profile State Management using SQLite + Dynamic RAG"""
    logger.info(f"[LLM Intent] Processing request | Session ID: '{session_id}' | Input: \"{user_text}\"")

    # 1. Fetch or create session record
    db_session = db.query(UserSessionModel).filter(UserSessionModel.session_id == session_id).first()
    
    if not db_session:
        logger.info(f"[LLM Intent] Creating new SQLite record for Session ID: '{session_id}'")
        default_profile = {
            "age": None,
            "marital_status": None,
            "annual_income": None,
            "occupation": None,
            "additional_notes": "" # NEW: Flexible field for dynamic eligibility data
        }
        db_session = UserSessionModel(session_id=session_id, profile=default_profile)
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
    
    current_profile = db_session.profile
    
    # ---------------------------------------------------------
    # 2. RAG RETRIEVAL: Query Translation & Search
    # ---------------------------------------------------------
    
    # A. Translate the Telugu text to an English search query
    translation_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "system", 
            "content": f"You are a translator. Translate the following Telugu text into a short, keyword-rich English search query for finding government welfare schemes. Include the current profile details if relevant. Profile: {json.dumps(current_profile)}"
        }, {
            "role": "user", 
            "content": user_text
        }],
        temperature=0.0 # 0.0 means maximum predictability
    )
    
    english_search_query = translation_response.choices[0].message.content.strip() # type: ignore
    logger.info(f"[RAG] Translated English Search Query: '{english_search_query}'")
    
    # B. Query ChromaDB using the English translated text
    rag_results = schemes_collection.query(
        query_texts=[english_search_query],
        n_results=2 # Fetch the top 2 most relevant schemes
    )
    
    retrieved_context = ""
    if rag_results['documents'] and rag_results['documents'][0]:
        for doc in rag_results['documents'][0]:
            retrieved_context += f"- {doc}\n\n"
            
    logger.info(f"[RAG] Retrieved Schemes for context:\n{retrieved_context}")

    # 3. Dynamic Agentic Prompt
    system_prompt = f"""
    You are an expert, empathetic government caseworker for rural women in Telangana.
    You speak completely in natural, polite Telugu script.

    CURRENT USER PROFILE:
    {json.dumps(current_profile)}

    OFFICIAL SCHEMES (RETRIEVED FROM DATABASE):
    {retrieved_context}

    USER LATEST STATEMENT:
    "{user_text}"

    EXECUTION STEPS:
    Step 1: Extract any new information the user provided and update the profile fields. Put any specific scheme-related details (e.g., 'pregnant', 'has ration card') into "additional_notes".
    Step 2: Analyze the OFFICIAL SCHEMES against the CURRENT USER PROFILE.
    Step 3: Decide what to do next:
            - IF you don't know the user's basic details (age, income), set "survey_complete": false and ask ONE basic question.
            - IF you have basic details but the OFFICIAL SCHEMES require specific eligibility (e.g., White Ration Card, Government Hospital), set "survey_complete": false and ask ONE targeted question to check that specific criteria.
            - IF the user meets all criteria for a retrieved scheme, set "survey_complete": true and recommend the scheme in Telugu, explaining exactly why they qualify.

    Respond ONLY in valid JSON matching this exact structure:
    {{
        "updated_profile": {{
            "age": integer or null,
            "marital_status": string or null,
            "annual_income": integer or null,
            "occupation": string or null,
            "additional_notes": string
        }},
        "next_response_telugu": "Your Telugu question OR recommendation here",
        "survey_complete": boolean
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        ai_output = json.loads(response.choices[0].message.content) # type: ignore
        
        # 4. Update SQLite record with new profile
        db_session.profile = ai_output["updated_profile"]
        db.commit()
        db.refresh(db_session)
        
        logger.info(f"[LLM Intent] Updated DB | Complete: {ai_output['survey_complete']}")
        return ai_output

    except Exception as e:
        logger.error(f"[LLM Intent] Error in session '{session_id}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def generate_audio_service(text: str, filepath: str):
    """Handles Telugu Text -> MP3 conversion"""
    if not text.strip():
        logger.warning("[TTS Service] Attempted audio generation with empty text string.")
        raise HTTPException(status_code=400, detail="Text cannot be empty")
        
    logger.info(f"[TTS Service] Generating audio file at '{filepath}' for text: \"{text[:40]}...\"")
    
    try:
        with client.audio.speech.with_streaming_response.create(
            model="tts-1", voice="nova", input=text
        ) as response:
            response.stream_to_file(filepath)
            
        logger.info(f"[TTS Service] Success | Generated file: '{filepath}'")

    except Exception as e:
        logger.error(f"[TTS Service] Error generating audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# API ROUTE HANDLERS
# =====================================================================

@app.get("/")
def read_root():
    return {"status": "active", "message": "PRAGATI Voice Helpline API is running with SQLite backend"}


@app.post("/api/v1/transcribe")
async def transcribe_endpoint(audio_file: UploadFile = File(...)):
    logger.info("--> POST /api/v1/transcribe request received")
    text = await transcribe_service(audio_file)
    return {"transcription": text}


@app.post("/api/v1/process-intent")
async def process_intent_endpoint(request: IntentRequest, db: Session = Depends(get_db)):
    return await process_intent_service(request.session_id, request.user_text, db)


@app.post("/api/v1/generate-audio")
async def generate_audio_endpoint(text: str, background_tasks: BackgroundTasks):
    logger.info("--> POST /api/v1/generate-audio request received")
    filename = f"response_{uuid.uuid4().hex[:8]}.mp3"
    filepath = f"./{filename}"
    
    await generate_audio_service(text, filepath)
    background_tasks.add_task(os.remove, filepath)
    logger.info(f"Scheduled cleanup for temporary file: '{filepath}'")
    
    return FileResponse(path=filepath, media_type="audio/mpeg", filename=filename)


@app.post("/api/v1/voice-chat")
async def voice_chat_endpoint(
    session_id: str = Form(...),
    audio_file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None, # type: ignore
    db: Session = Depends(get_db)
):
    logger.info(f"==========================================================")
    logger.info(f"--> [Voice Pipeline] New request | Session ID: '{session_id}'")
    
    try:
        # Step 1: Speech to Text
        logger.info("[Voice Pipeline] Step 1/3: Converting speech to text...")
        user_text = await transcribe_service(audio_file)
        intent_result = await process_intent_service(session_id, user_text, db)
        telugu_response = intent_result["next_response_telugu"]
        
        # Step 3: Text to Speech
        logger.info("[Voice Pipeline] Step 3/3: Synthesizing voice response...")
        filename = f"chat_{uuid.uuid4().hex[:8]}.mp3"
        filepath = f"./{filename}"
        await generate_audio_service(telugu_response, filepath)
        
        if background_tasks:
            background_tasks.add_task(os.remove, filepath)
            logger.info(f"[Voice Pipeline] Scheduled cleanup for file: '{filepath}'")
            
        logger.info(f"[Voice Pipeline] Completed successfully for Session ID: '{session_id}'")
        logger.info(f"==========================================================")
            
        return FileResponse(
            path=filepath,
            media_type="audio/mpeg",
            filename=filename,
            headers={
                "X-User-Transcribed-Text": urllib.parse.quote(user_text),
                "X-Survey-Complete": str(intent_result["survey_complete"]),
                "X-Current-Profile": urllib.parse.quote(json.dumps(intent_result["updated_profile"]))
            }
        )
    except Exception as e:
        logger.error(f"[Voice Pipeline] Error in session '{session_id}': {str(e)}")
        raise e


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)