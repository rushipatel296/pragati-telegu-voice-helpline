import os
import json
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# Load API key
load_dotenv()

def ingest_knowledge_base():
    print("🚀 Initializing ChromaDB...")
    
    # 1. Setup ChromaDB to save to a local folder named "chroma_db"
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    # 2. Configure OpenAI's embedding model
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"
    )
    
    # 3. Create a collection (similar to a SQL table)
    # If we run this script again, we delete the old one to avoid duplicates
    try:
        chroma_client.delete_collection(name="telangana_schemes")
    except Exception:
        pass # Collection doesn't exist yet, which is fine
        
    collection = chroma_client.create_collection(
        name="telangana_schemes",
        embedding_function=openai_ef # type: ignore
    )
    
    # 4. Our "Documents" (Official Telangana Schemes Knowledge Base)
    schemes_data = [
        {
            "id": "scheme_1",
            "name": "Kalyana Lakshmi / Shaadi Mubarak",
            "description": "Financial assistance of Rs. 1,00,116 for the marriage of girls from SC, ST, BC, and EBC families.",
            "eligibility": "Must be a resident of Telangana, bride must be 18+ years old, and combined family income must not exceed Rs. 2,00,000 per annum (urban) or Rs. 1,50,000 (rural)."
        },
        {
            "id": "scheme_2",
            "name": "KCR Kit Scheme",
            "description": "Provides financial assistance and a kit with 16 essential items for pregnant women and newborn babies to reduce infant mortality.",
            "eligibility": "Women giving birth in a government hospital in Telangana. Maximum of two deliveries."
        },
        {
            "id": "scheme_3",
            "name": "Arogyasri Health Care",
            "description": "Free healthcare and hospitalization for catastrophic illnesses requiring surgeries/therapies.",
            "eligibility": "Families holding a White Ration Card (BPL families) in Telangana."
        },
        {
            "id": "scheme_4",
            "name": "Aasara Pensions (Widow / Single Women)",
            "description": "Monthly pension of Rs. 2,016 to support vulnerable women, widows, and single women.",
            "eligibility": "Must be a resident of Telangana, belonging to BPL category. Single women must be unmarried and above 30 years (rural) or 35 years (urban)."
        }
    ]
    
    print(f"📥 Embedding and storing {len(schemes_data)} schemes...")
    
    # 5. Prepare the data for ChromaDB
    documents = []
    metadatas = []
    ids = []
    
    for scheme in schemes_data:
        # We embed a combination of name, description, and eligibility for best search accuracy
        search_text = f"Scheme: {scheme['name']}\nDescription: {scheme['description']}\nEligibility: {scheme['eligibility']}"
        documents.append(search_text)
        
        # Metadata allows us to filter or extract specific fields later
        metadatas.append({
            "name": scheme['name'],
            "description": scheme['description'],
            "eligibility": scheme['eligibility']
        })
        
        ids.append(scheme["id"])
        
    # 6. Insert into Vector Database
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    print("✅ Knowledge Base successfully ingested into ChromaDB!")

if __name__ == "__main__":
    print("Starting ingestion..")
    ingest_knowledge_base()