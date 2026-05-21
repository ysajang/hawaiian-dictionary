"""
Hawaiian-English AI Dictionary Web App
Streamlit application entry point.

Architecture:
    Google Sheets (4 sheets) → sheets_loader.py (cached)
    User Input → matcher.py (block check + disclaimer detection)
    Gemini API → gemini_client.py (streaming response)
    Auth → auth.py (password gate)
"""

import streamlit as st
from sheets_loader import load_all_sheets
from auth import check_auth
from matcher import check_blocked, find_disclaimers
from gemini_client import get_client, generate_stream

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
MAX_HISTORY_TURNS = 20


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────
def trim_history():
    """Keep only the last MAX_HISTORY_TURNS pairs of messages."""
    messages = st.session_state.get("messages", [])
    if len(messages) > MAX_HISTORY_TURNS * 2:
        st.session_state.messages = messages[-(MAX_HISTORY_TURNS * 2):]


# ──────────────────────────────────────────────
# Page Configuration
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Olii — Hawaiian Context Dictionary",
    page_icon="🌿",
    layout="centered",
)

# ──────────────────────────────────────────────
# Custom CSS — matching design deck palette
# ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&display=swap');

    /* Main content gradient — sage top to cream bottom */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #D5E1DC 0%, #F5F0EA 25%);
    }
    [data-testid="stHeader"] {
        background: transparent;
    }

    /* Chat input styling */
    .stChatInput textarea::placeholder {
        color: #8BA39B;
        font-size: 0.88rem;
    }

    /* Sidebar refinement */
    [data-testid="stSidebar"] {
        background-color: #D5E1DC;
    }
    [data-testid="stSidebar"] .stMarkdown p {
        font-size: 0.9rem;
        line-height: 1.65;
        color: #3D4D47;
    }
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #2D2D2D;
        font-family: 'Playfair Display', Georgia, serif;
        font-weight: 700;
        font-size: 1.1rem;
    }

    /* Header area */
    .olii-header {
        text-align: center;
        padding: 0.5rem 0 1.5rem 0;
    }
    .olii-header h1 {
        font-family: 'Playfair Display', Georgia, serif;
        color: #2D2D2D;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0;
        line-height: 1.1;
    }
    .olii-header .subtitle {
        font-family: sans-serif;
        color: #5B7B71;
        font-size: 0.8rem;
        letter-spacing: 0.25em;
        text-transform: uppercase;
        margin-top: 0.3rem;
    }

    /* Disclaimer block styling */
    .stAlert {
        border-radius: 8px;
    }

    /* Chat message refinement */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
    }

    /* Tagline below header */
    .olii-tagline {
        text-align: center;
        color: #8BA39B;
        font-size: 0.82rem;
        font-style: italic;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Load Google Sheets Data (cached by TTL)
# ──────────────────────────────────────────────
SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL", "")

if not SPREADSHEET_URL:
    st.error("SPREADSHEET_URL is not configured in secrets.")
    st.stop()

data = load_all_sheets(SPREADSHEET_URL)

if not data["system_prompt"]:
    st.warning("System prompt is empty. The AI may not behave as expected.")

config = data["config"]
PASSWORD = config.get("password", "")
MODEL_NAME = config.get("model", "gemini-2.5-flash")
try:
    MAX_TOKENS = int(config.get("max_tokens", "1024"))
except (ValueError, TypeError):
    MAX_TOKENS = 1024
APP_TITLE = config.get("app_title", "Olii")
APP_SUBTITLE = config.get("app_subtitle", "")

# ──────────────────────────────────────────────
# Authentication Gate
# ──────────────────────────────────────────────
if not check_auth(PASSWORD):
    st.stop()

# ──────────────────────────────────────────────
# Chat UI Header
# ──────────────────────────────────────────────
st.markdown(f"""
<div class="olii-header">
    <h1>{APP_TITLE}</h1>
    <div class="subtitle">Hawaiian Context Dictionary</div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:1rem 0 0.5rem 0;">
            <span style="font-family:'Playfair Display',Georgia,serif;
                          font-size:1.8rem; font-weight:700;
                          color:#2D2D2D;">
                Olii
            </span>
            <br>
            <span style="font-family:sans-serif; font-size:0.65rem;
                          letter-spacing:0.2em; color:#5B7B71;
                          text-transform:uppercase;">
                Hawaiian Context Dictionary
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    st.markdown("### About Olii")
    st.markdown(
        "Language is more than just a communication tool — "
        "it carries cultural identity, knowledge, and history. "
        "**Olii** was born from the belief that technology can be "
        "a guardian of culture, not a destroyer.\n\n"
        "We are not a definitive dictionary or an ultimate authority. "
        "Olii is a **patient, respectful guide**, supporting learners "
        "in approaching ʻŌlelo Hawaiʻi with clarity, care, and "
        "cultural awareness."
    )
    st.markdown("---")

    st.markdown("### The Olii Guidelines")
    st.markdown(
        "**Context First** — Cultural and situational context "
        "before direct translation.\n\n"
        "**Supportive & Suggestive** — Corrections are offered gently, "
        "never evaluatively.\n\n"
        "**Built-in Humility** — For deeper learning and sacred chants, "
        "users are directed to consult with human Kumu.\n\n"
        "**Explicit Avoidance** — No aggressive tones, exclusionary "
        "language, or authoritative voices."
    )
    st.markdown("---")

    st.markdown("### Ethical Reference")
    st.markdown(
        "Grounded in the **UN Declaration on the Rights of Indigenous "
        "Peoples** and **UNESCO AI Ethics Recommendations**.\n\n"
        "Olii maintains strict standards of accuracy, avoids "
        "unverified information, and clearly acknowledges "
        "uncertainty when necessary."
    )
    st.markdown("---")

    st.caption(
        "Reference: Pukui & Elbert Hawaiian Dictionary tradition."
    )
    st.markdown("")
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ──────────────────────────────────────────────
# Chat History Init & Display
# ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ──────────────────────────────────────────────
# Chat Input Processing
# ──────────────────────────────────────────────
if prompt := st.chat_input("Beyond just 'family,' what is the deeper significance of 'Ohana' in the context of Hawaiian ancestry and protection?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Step 1: Blocked Pattern Check (no AI call)
    blocked_response = check_blocked(prompt, data["blocked_patterns"])
    if blocked_response:
        st.session_state.messages.append({
            "role": "assistant",
            "content": blocked_response,
        })
        with st.chat_message("assistant"):
            st.markdown(blocked_response)
        st.rerun()

    # Step 2: Disclaimer Detection
    disclaimers = find_disclaimers(prompt, data["word_categories"])

    # Step 3: Gemini Streaming Response
    with st.chat_message("assistant"):
        disclaimer_block = ""
        if disclaimers:
            disclaimer_block = "\n\n".join(disclaimers) + "\n\n---\n\n"
            st.markdown(disclaimer_block)

        try:
            client = get_client()
            stream = generate_stream(
                client=client,
                model_name=MODEL_NAME,
                system_prompt=data["system_prompt"],
                chat_history=st.session_state.messages,
                disclaimers=disclaimers,
                max_tokens=MAX_TOKENS,
            )
            ai_response = st.write_stream(stream)
        except Exception as e:
            ai_response = f"⚠️ Service temporarily unavailable: {str(e)}"
            st.error(ai_response)

        full_response = disclaimer_block + (ai_response or "")
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
        })

    # Step 4: Trim history
    trim_history()
