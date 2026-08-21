import os
import uuid
import json
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import uvicorn
import urllib.parse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler()  
    ]
)
logger = logging.getLogger("PRAGATI_BOT")


load_dotenv()
client = OpenAI()

app = FastAPI(title="PRAGATI Helpline Voice Bot")

user_sessions = {}

class IntentRequest(BaseModel):
    session_id: str
    user_text: str


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


async def process_intent_service(session_id: str, user_text: str) -> dict:
    """Handles User Profile State Management + LLM Reasoning"""
    logger.info(f"[LLM Intent] Processing request | Session ID: '{session_id}' | Input Text: \"{user_text}\"")

    if session_id not in user_sessions:
        logger.info(f"[LLM Intent] Creating new session profile for Session ID: '{session_id}'")
        user_sessions[session_id] = {
            "age": None,
            "marital_status": None,
            "annual_income": None,
            "occupation": None
        }
    
    current_profile = user_sessions[session_id]
    logger.info(f"[LLM Intent] Session '{session_id}' state before LLM call: {current_profile}")
    
    system_prompt = f"""
    You are an empathetic AI assistant guiding rural women in Telangana to find government schemes.
    You speak completely in natural, polite Telugu script.

    STRICT CONSTRAINTS:
    1. You are ONLY allowed to collect: age, marital_status, annual_income, occupation.
    2. NEVER ask for any other information (e.g., location, address, family size, district, name).
    3. NEVER ask follow-up questions once all 4 fields are known.

    CURRENT PROFILE:
    {json.dumps(current_profile)}

    USER LATEST STATEMENT:
    "{user_text}"

    EXECUTION STEPS:
    Step 1: Extract new information and update profile fields.
    Step 2: Check updated profile:
            - IF ANY of the 4 fields are null:
              * "survey_complete": false
              * Ask ONE polite question in Telugu to gather ONE missing field.
            - IF ALL 4 fields are NOT null:
              * "survey_complete": true
              * Recommend 1 to 3 relevant Telangana government schemes in polite Telugu.

    Respond ONLY in valid JSON matching this exact structure:
    {{
        "updated_profile": {{
            "age": integer or null,
            "marital_status": string or null,
            "annual_income": integer or null,
            "occupation": string or null
        }},
        "next_response_telugu": "Your Telugu text here",
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
        
        ai_output = json.loads(response.choices[0].message.content)
        user_sessions[session_id] = ai_output["updated_profile"]
        
        logger.info(f"[LLM Intent] Success | Session: '{session_id}' | Complete: {ai_output['survey_complete']} | Updated Profile: {ai_output['updated_profile']}")
        logger.info(f"[LLM Intent] Next Response (Telugu): \"{ai_output['next_response_telugu']}\"")
        
        return ai_output

    except Exception as e:
        logger.error(f"[LLM Intent] Error processing intent for session '{session_id}': {str(e)}", exc_info=True)
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
        logger.error(f"[TTS Service] Error generating audio file '{filepath}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"status": "active", "message": "PRAGATI Voice Helpline API is running"}


@app.post("/api/v1/transcribe")
async def transcribe_endpoint(audio_file: UploadFile = File(...)):
    logger.info("--> POST /api/v1/transcribe request received")
    text = await transcribe_service(audio_file)
    return {"transcription": text}


@app.post("/api/v1/process-intent")
async def process_intent_endpoint(request: IntentRequest):
    logger.info(f"--> POST /api/v1/process-intent request received for session '{request.session_id}'")
    return await process_intent_service(request.session_id, request.user_text)


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
    background_tasks: BackgroundTasks = None
):
    logger.info(f"==========================================================")
    logger.info(f"--> [Voice Pipeline] New request | Session ID: '{session_id}'")
    
    try:
        # Step 1: Speech to Text
        logger.info("[Voice Pipeline] Step 1/3: Converting speech to text...")
        user_text = await transcribe_service(audio_file)
        
        # Step 2: Intent Engine
        logger.info("[Voice Pipeline] Step 2/3: Evaluating state and next intent...")
        intent_result = await process_intent_service(session_id, user_text)
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
                # Safely encode the Telugu text for HTTP transit
                "X-User-Transcribed-Text": urllib.parse.quote(user_text),
                "X-Survey-Complete": str(intent_result["survey_complete"]),
                "X-Current-Profile": urllib.parse.quote(json.dumps(intent_result["updated_profile"]))
            }
        )
    except Exception as e:
        logger.error(f"[Voice Pipeline] Pipeline failed for session '{session_id}': {str(e)}")
        logger.info(f"==========================================================")
        raise e


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)