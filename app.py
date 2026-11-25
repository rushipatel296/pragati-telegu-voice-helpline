import json
import os
import urllib.parse
import uuid

import requests
import streamlit as st

from demo_data import SCENARIOS


API_URL = os.getenv("PRAGATI_API_URL", "").rstrip("/")

st.set_page_config(
    page_title="PRAGATI Telugu Voice Helpline",
    page_icon="🎙️",
    layout="wide",
)

st.title("PRAGATI")
st.caption("A Telugu-first AI caseworker concept for navigating Telangana welfare schemes.")

with st.sidebar:
    st.header("Demo controls")
    mode_options = ["Guided public demo"]
    if API_URL:
        mode_options.append("Live voice backend")
    mode = st.radio("Mode", mode_options)
    st.divider()
    st.markdown("**Production pipeline**")
    st.caption("Voice → transcription → profile extraction → scheme retrieval → Telugu response → speech")

if mode == "Guided public demo":
    st.info(
        "This public demo is deterministic and API-free, so it cannot generate usage charges. "
        "It illustrates the product flow without claiming to make an official eligibility decision."
    )

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Try an illustrative case")
        scenario_name = st.selectbox("Choose a caller situation", list(SCENARIOS))
        scenario = SCENARIOS[scenario_name]

        audio_file = st.audio_input("Optional: record a Telugu message")
        if audio_file:
            st.audio(audio_file)
            st.caption(
                "Recording captured locally. The public demo does not upload or transcribe it; "
                "select a sample case below to continue."
            )

        if st.button("Run guided conversation", type="primary"):
            st.session_state["demo_result"] = scenario_name

        selected_result = st.session_state.get("demo_result")
        if selected_result:
            result = SCENARIOS[selected_result]
            with st.chat_message("user"):
                st.write(result["transcript"])
                st.caption(result["translation"])
            with st.chat_message("assistant"):
                st.write(result["response"])
                st.caption(f"Potential match: {result['scheme']}")

    with right:
        st.subheader("Caseworker state")
        selected_result = st.session_state.get("demo_result")
        if selected_result:
            result = SCENARIOS[selected_result]
            st.json(result["profile"])
            st.markdown(f"**Why it surfaced:** {result['reason']}")
            st.link_button("Check the official source", result["source"])
        else:
            st.caption("Run a guided conversation to see the structured profile and retrieval result.")

    st.divider()
    st.warning(
        "Prototype only—not an official government service or eligibility determination. "
        "Scheme rules can change; always verify with the linked Telangana government source or MeeSeva."
    )

else:
    st.info("Live mode sends the recording to the configured PRAGATI backend.")
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_profile" not in st.session_state:
        st.session_state.current_profile = {}
    if "last_audio_hash" not in st.session_state:
        st.session_state.last_audio_hash = None

    left, right = st.columns([3, 2])
    with left:
        audio_file = st.audio_input("Record a Telugu message")
        if audio_file:
            audio_bytes = audio_file.getvalue()
            current_hash = hash(audio_bytes)
            if st.session_state.last_audio_hash != current_hash:
                st.session_state.last_audio_hash = current_hash
                files = {"audio_file": ("user_voice.wav", audio_bytes, "audio/wav")}
                data = {"session_id": st.session_state.session_id}

                with st.spinner("PRAGATI is listening…"):
                    try:
                        response = requests.post(
                            f"{API_URL}/api/v1/voice-chat",
                            files=files,
                            data=data,
                            timeout=90,
                        )
                        response.raise_for_status()
                        st.audio(response.content, format="audio/mp3")
                        transcript = urllib.parse.unquote(
                            response.headers.get("X-User-Transcribed-Text", "")
                        )
                        profile_json = urllib.parse.unquote(
                            response.headers.get("X-Current-Profile", "{}")
                        )
                        st.session_state.current_profile = json.loads(profile_json)
                        st.session_state.chat_history.extend(
                            [
                                {"role": "user", "text": transcript},
                                {"role": "assistant", "text": "Audio response generated"},
                            ]
                        )
                    except (requests.RequestException, json.JSONDecodeError) as exc:
                        st.error(f"The live backend could not complete this request: {exc}")

        st.subheader("Conversation")
        for chat in st.session_state.chat_history:
            with st.chat_message(chat["role"]):
                st.write(chat["text"])

    with right:
        st.subheader("Caseworker state")
        st.json(st.session_state.current_profile)
