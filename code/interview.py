import json
import uuid
import time
import requests
import streamlit as st

API_URL = "https://xakur8y87j.execute-api.eu-north-1.amazonaws.com/Prod/"

st.set_page_config(page_title="Study Chat", page_icon="💬", layout="centered")

# ------- Consent flow -------
if "consent_given" not in st.session_state:
    st.session_state.consent_given = None  # None = not decided yet

if st.session_state.consent_given is None:
    st.title("Study Consent")
    st.write("By continuing you consent to anonymous logging of messages for research.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, I consent"):
            st.session_state.consent_given = True
    with col2:
        if st.button("No, I do not consent"):
            st.session_state.consent_given = False
elif st.session_state.consent_given is False:
    st.warning("You did not consent. You cannot use this app.")
else:
    # ------- Main chat app -------
    st.title("Study Chat")
    st.caption("You have consented. Let's get started!")

    # ------- session id and interview id from URL or defaults -------
    def get_param(params, key, default):
        try:
            val = params.get(key)
            if isinstance(val, list):
                return val[0] if val else default
            return val if val else default
        except Exception:
            return default

    try:
        params = st.query_params
    except Exception:
        params = st.experimental_get_query_params()

    sid_default = str(uuid.uuid4())
    sid = get_param(params, "sid", sid_default)
    iid = get_param(params, "iid", "PART_TIME")

    with st.sidebar:
        st.subheader("Session")
        st.write(f"Session ID: `{sid}`")
        st.write(f"Interview ID: `{iid}`")

    if "history" not in st.session_state:
        st.session_state.history = []
    if "ended" not in st.session_state:
        st.session_state.ended = False

    # render history
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # chat input
    placeholder = "Type your message"
    if st.session_state.ended:
        st.info("Session ended. Refresh the page or change sid to start a new one.")
        user_text = None
    else:
        user_text = st.chat_input(placeholder)

    def call_backend(message: str) -> str:
        payload = {
            "route": "next",
            "payload": {
                "session_id": sid,
                "interview_id": iid,
                "user_message": message
            }
        }
        r = requests.post(API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        if not r.ok:
            try:
                info = r.json()
            except Exception:
                info = {"message": r.text}
            raise RuntimeError(f"Backend error {r.status_code}: {info.get('message', 'no message')}")
        data = r.json()
        return data.get("message") or json.dumps(data)

    if user_text:
        st.session_state.history.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.write(user_text)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            try:
                reply_text = call_backend(user_text)
                acc = ""
                for ch in reply_text:
                    acc += ch
                    placeholder.write(acc)
                    time.sleep(0.005)
            except Exception as e:
                st.error(str(e))
                reply_text = "There was an error reaching the server. Please try again."
                placeholder.write(reply_text)

        st.session_state.history.append({"role": "assistant", "content": reply_text})

        if user_text.strip().lower() in {"stop", "end", "quit"}:
            st.session_state.ended = True
            st.toast("Session ended.", icon="🛑")
        st.rerun()
