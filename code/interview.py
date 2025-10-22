# streamlit_app.py
import json
import uuid
import time
import requests
import streamlit as st

API_URL = "https://xakur8y87j.execute-api.eu-north-1.amazonaws.com/Prod/"

st.set_page_config(page_title="Study Chat", page_icon="💬", layout="centered")
st.title("Study Chat")
st.caption("By continuing you consent to anonymous logging of messages for research.")


# ------- session id and interview id from URL or defaults -------
def get_param(params, key, default):
    # Works for both st.query_params (new) and experimental_get_query_params (old)
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
sid = get_param(params, "sid", "1234")
iid = get_param(params, "iid", "PART_TIME")

with st.sidebar:
    st.subheader("Session")
    st.write(f"Session ID: `{sid}`")
    st.write(f"Interview ID: `{iid}`")
    st.write("Share a link like:")
    st.code(f"https://YOUR_HOST:7860/?sid=FRIEND123&iudebug=1&iid=PART_TIME", language="text")
    st.caption("Use sid to tag invitees. iid lets you switch study variants.")


# ------- state -------
if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: {"role": "user"|"assistant", "content": "..."}
if "ended" not in st.session_state:
    st.session_state.ended = False


# ------- render history -------
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# ------- chat input -------
placeholder = "Type your message"
if st.session_state.ended:
    st.info("Session ended. Refresh the page or change sid to start a new one.")
    user_text = None
else:
    user_text = st.chat_input(placeholder)

# ------- send turn -------
def call_backend(message: str) -> str:
    print(sid, iid, message)
    payload = {
        "route": "next",
        "payload": {
            "session_id": sid,
            "interview_id": iid,
            "user_message": message
        }
    }
    r = requests.post(API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
    # API Gateway often returns JSON on error with status 4xx or 5xx
    if not r.ok:
        try:
            info = r.json()
        except Exception:
            info = {"message": r.text}
        raise RuntimeError(f"Backend error {r.status_code}: {info.get('message', 'no message')}")
    data = r.json()
    reply = data.get("message") or json.dumps(data)
    print(data)
    return reply

if user_text:
    # Append user message
    st.session_state.history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    # Call backend and stream a simple typing effect
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            reply_text = call_backend(user_text)
            # simple typeout
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


# ------- utilities -------
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Clear chat"):
        st.session_state.history = []
        st.session_state.ended = False
        st.rerun()

with col2:
    # limit to N turns if you wish
    MAX_TURNS = 200
    if len(st.session_state.history) >= MAX_TURNS and not st.session_state.ended:
        st.session_state.ended = True
        st.warning("Turn limit reached.")