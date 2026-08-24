import streamlit as st
import requests
import json
import urllib.parse
# ❌ REMOVED: from audio_recorder_streamlit import audio_recorder

# Backend API URL
API_URL = "http://localhost:8000/api/v1/voice-chat"

st.set_page_config(page_title="PRAGATI Voice Helpline", page_icon="🎙️", layout="wide")

st.title("🎙️ PRAGATI: Telugu Voice Helpline")
st.markdown("An AI caseworker connecting rural women in Telangana to government schemes via voice.")

# Initialize session state for the UI
if "session_id" not in st.session_state:
    st.session_state.session_id = "demo_user_1" 
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_profile" not in st.session_state:
    st.session_state.current_profile = {}
# NEW: Track the last audio file so we don't accidentally send it twice
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None 

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("1. Speak in Telugu")
    
    # ✅ FIX: Use Streamlit's official built-in microphone widget!
    audio_file = st.audio_input("Click the microphone to record")
    
    if audio_file:
        audio_bytes = audio_file.getvalue()
        
        # ✅ FIX: Only trigger the backend if this is a NEW audio recording
        current_hash = hash(audio_bytes)
        if st.session_state.last_audio_hash != current_hash:
            st.session_state.last_audio_hash = current_hash
            
            st.success("Audio captured! Sending to PRAGATI AI...")
            
            files = {"audio_file": ("user_voice.wav", audio_bytes, "audio/wav")}
            data = {"session_id": st.session_state.session_id}
            
            with st.spinner("AI is thinking..."):
                try:
                    response = requests.post(API_URL, files=files, data=data)
                    
                    if response.status_code == 200:
                        # 1. Play the AI's audio response
                        st.audio(response.content, format="audio/mp3")
                        
                        # 2. Extract metadata
                        transcribed_text = urllib.parse.unquote(response.headers.get("X-User-Transcribed-Text", ""))
                        profile_json = urllib.parse.unquote(response.headers.get("X-Current-Profile", "{}"))
                        st.session_state.current_profile = json.loads(profile_json)
                        
                        # 3. Update chat history
                        st.session_state.chat_history.append({"role": "user", "text": transcribed_text})
                        st.session_state.chat_history.append({"role": "assistant", "text": "🔊 [Audio Response Generated]"})
                        
                    else:
                        st.error(f"Backend Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

    st.divider()
    st.subheader("Conversation Transcript")
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.info(f"🗣️ **You:** {chat['text']}")
        else:
            st.success(f"🤖 **PRAGATI:** {chat['text']}")

with col2:
    st.subheader("🧠 AI Brain (Live State)")
    st.markdown("Watch the AI update the database in real-time as you speak.")
    
    st.json(st.session_state.current_profile)
    
    if st.session_state.current_profile:
        st.caption("✅ Schema validation active")