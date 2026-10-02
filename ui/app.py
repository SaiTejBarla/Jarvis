"""
ui/app.py — JARVIS Streamlit web dashboard (Phase 4).

Run with:
    streamlit run ui/app.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

import config
from core.engine import JarvisEngine

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JARVIS",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    body, .main { background-color: #0a0a0f; color: #c8d8e8; }
    .block-container { padding-top: 1rem; }
    .stTextInput > div > div > input {
        background-color: #0d1b2a; color: #00d4ff;
        border: 1px solid #00d4ff55; border-radius: 6px;
    }
    .stButton > button {
        background-color: #00d4ff18; color: #00d4ff;
        border: 1px solid #00d4ff44; border-radius: 6px;
    }
    .stButton > button:hover { background-color: #00d4ff33; }
    .user-msg {
        background: #0d1b2a; border-left: 3px solid #00d4ff;
        padding: 8px 14px; border-radius: 0 6px 6px 0; margin: 6px 0; color: #ddeeff;
    }
    .jarvis-msg {
        background: #071a07; border-left: 3px solid #00ff88;
        padding: 8px 14px; border-radius: 0 6px 6px 0; margin: 6px 0; color: #d0ffd0;
    }
    .tool-msg {
        background: #1a1400; border-left: 3px solid #ffcc00;
        padding: 6px 14px; border-radius: 0 6px 6px 0; margin: 4px 0;
        color: #fff3b0; font-size: 0.88em;
    }
    .status-ok  { color: #00ff88; font-weight: bold; }
    .status-err { color: #ff4444; font-weight: bold; }
    .section-header { color: #00d4ff; font-size: 0.8em; text-transform: uppercase;
                      letter-spacing: 1px; margin-top: 12px; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "engine" not in st.session_state:
    st.session_state.engine = JarvisEngine()
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {role, content, ts, source}

engine: JarvisEngine = st.session_state.engine


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Control Panel")
    st.markdown("---")

    # Status indicators
    st.markdown("<div class='section-header'>System Status</div>", unsafe_allow_html=True)
    ollama_ok = True
    try:
        import requests as _req
        _req.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=1)
    except Exception:
        ollama_ok = False

    mem_ok = engine.memory is not None
    st.markdown(
        f"<span class='{'status-ok' if ollama_ok else 'status-err'}'>●</span> "
        f"Ollama ({'online' if ollama_ok else 'offline'})",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span class='{'status-ok' if mem_ok else 'status-err'}'>●</span> "
        f"Memory ({'active' if mem_ok else 'unavailable'})",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span class='status-ok'>●</span> Tools (active)",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Model switcher
    st.markdown("<div class='section-header'>LLM Model</div>", unsafe_allow_html=True)
    new_model = st.text_input("Ollama model", value=config.OLLAMA_MODEL, key="model_input")
    if new_model != config.OLLAMA_MODEL:
        config.OLLAMA_MODEL = new_model
        engine.reset_memory()
        st.success(f"Switched to {new_model}")

    st.markdown("---")

    # Actions
    st.markdown("<div class='section-header'>Actions</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Reset Chat"):
            engine.reset_memory()
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("🧹 Clear Facts"):
            if engine.memory:
                import sqlite3
                with sqlite3.connect(engine.memory._db_path) as conn:
                    conn.execute("DELETE FROM facts")
            st.rerun()

    st.markdown("---")

    # Memory facts panel
    st.markdown("<div class='section-header'>Known Facts</div>", unsafe_allow_html=True)
    if engine.memory:
        facts = engine.memory.all_facts()
        if facts:
            for k, v in facts.items():
                st.markdown(f"**{k}:** {v}")
        else:
            st.caption("No facts stored yet.")

        # Add fact manually
        with st.expander("➕ Add fact"):
            fkey = st.text_input("Key", placeholder="e.g. user_city", key="fkey")
            fval = st.text_input("Value", placeholder="e.g. Hyderabad", key="fval")
            if st.button("Save fact") and fkey and fval:
                engine.memory.store_fact(fkey, fval)
                st.success("Saved!")
                st.rerun()
    else:
        st.caption("Memory unavailable.")

    st.markdown("---")

    # Notes quick view
    st.markdown("<div class='section-header'>Recent Notes</div>", unsafe_allow_html=True)
    notes_dir = config.DATA_DIR / "notes"
    if notes_dir.exists():
        notes = sorted(notes_dir.glob("note_*.md"), reverse=True)[:3]
        for n in notes:
            lines = n.read_text(encoding="utf-8").splitlines()
            preview = next((l.strip().lstrip("#").strip() for l in lines if l.strip()), n.stem)
            st.caption(f"📝 {preview[:40]}")
    else:
        st.caption("No notes yet.")

    st.markdown("---")
    st.caption(f"Model: `{config.OLLAMA_MODEL}`  |  JARVIS Phase 4")


# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='color:#00d4ff;text-align:center;letter-spacing:4px;'>J.A.R.V.I.S.</h1>"
    "<p style='color:#556;text-align:center;font-size:0.85em;'>"
    "Just A Rather Very Intelligent System — Phase 4</p>",
    unsafe_allow_html=True,
)

# Tabs: Chat | Tool Log | Notes | Audit
tab_chat, tab_tools, tab_notes, tab_audit = st.tabs(["💬 Chat", "🔧 Tool Log", "📝 Notes", "🔐 Audit Log"])

# ── Chat tab ──────────────────────────────────────────────────────────────────
with tab_chat:
    # Display messages
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            ts = msg.get("ts", "")
            source = msg.get("source", "llm")

            if role == "user":
                st.markdown(
                    f"<div class='user-msg'>🧑 <strong>You</strong> "
                    f"<span style='color:#445;font-size:0.8em'>{ts}</span><br>{content}</div>",
                    unsafe_allow_html=True,
                )
            elif source == "tool":
                st.markdown(
                    f"<div class='tool-msg'>🔧 <strong>JARVIS (tool)</strong> "
                    f"<span style='color:#554;font-size:0.8em'>{ts}</span><br>{content}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='jarvis-msg'>🤖 <strong>JARVIS</strong> "
                    f"<span style='color:#345;font-size:0.8em'>{ts}</span><br>{content}</div>",
                    unsafe_allow_html=True,
                )

    # Input
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input(
                "Message", placeholder="Ask JARVIS anything…",
                label_visibility="collapsed",
            )
        with col2:
            submitted = st.form_submit_button("Send ➤")

    if submitted and user_input.strip():
        ts_now = datetime.now().strftime("%H:%M")
        st.session_state.messages.append({
            "role": "user", "content": user_input, "ts": ts_now, "source": "user"
        })

        # Check if tool was used (compare before/after dispatcher)
        with st.spinner("JARVIS is thinking…"):
            # Peek at tool dispatch
            tool_result = None
            try:
                disp = engine._get_dispatcher()
                tool_result = disp.dispatch(user_input)
            except Exception:
                pass

            reply = engine.process(user_input)

        source = "tool" if tool_result else "llm"
        st.session_state.messages.append({
            "role": "jarvis", "content": reply, "ts": ts_now, "source": source
        })
        st.rerun()

# ── Tool log tab ──────────────────────────────────────────────────────────────
with tab_tools:
    st.markdown("#### Recent tool-sourced responses")
    tool_msgs = [m for m in st.session_state.messages if m.get("source") == "tool"]
    if not tool_msgs:
        st.info("No tool responses yet. Try asking for the weather, time, or a calculation.")
    for m in reversed(tool_msgs[-10:]):
        st.markdown(
            f"<div class='tool-msg'>🔧 {m['ts']} — {m['content']}</div>",
            unsafe_allow_html=True,
        )

# ── Notes tab ─────────────────────────────────────────────────────────────────
with tab_notes:
    st.markdown("#### Your notes")

    notes_dir = config.DATA_DIR / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    notes = sorted(notes_dir.glob("note_*.md"), reverse=True)

    if not notes:
        st.info("No notes yet. Say 'take a note: …' in chat or add one below.")

    for i, note_path in enumerate(notes, 1):
        content = note_path.read_text(encoding="utf-8").strip()
        with st.expander(f"📝 Note {i} — {note_path.stem.replace('note_', '')}"):
            st.markdown(content)
            if st.button(f"🗑️ Delete note {i}", key=f"del_{i}"):
                note_path.unlink()
                st.rerun()

    st.markdown("---")
    st.markdown("**Add a new note:**")
    new_note = st.text_area("Note content", placeholder="Write your note here…", key="new_note")
    if st.button("💾 Save note") and new_note.strip():
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        (notes_dir / f"note_{ts}.md").write_text(
            f"# Note — {_dt.now().strftime('%B %d, %Y %I:%M %p')}\n\n{new_note.strip()}\n",
            encoding="utf-8",
        )
        st.success("Note saved!")
        st.rerun()

# ── Audit log tab ─────────────────────────────────────────────────────────────
with tab_audit:
    st.markdown("#### Action Audit Log")

    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("🔄 Refresh"):
            st.rerun()

    try:
        from core.audit import AuditLog
        entries = AuditLog().recent(50)
        if not entries:
            st.info("No audit entries yet. Actions will appear here as you use JARVIS.")
        else:
            for e in entries:
                t = e.get("type", "")
                ts = e.get("ts", "")
                if t == "tool_call":
                    st.markdown(
                        f"<div class='tool-msg'>🔧 <b>{ts}</b> — tool: "
                        f"{e.get('tool','')} | {e.get('query','')[:60]}</div>",
                        unsafe_allow_html=True,
                    )
                elif t == "auth":
                    st.markdown(
                        f"<div class='user-msg'>🔐 <b>{ts}</b> — auth: "
                        f"{e.get('event','')} | {e.get('action','')[:60]}</div>",
                        unsafe_allow_html=True,
                    )
                elif t == "critical_action":
                    color = "status-err" if e.get("blocked") else "status-ok"
                    status = "BLOCKED" if e.get("blocked") else "ALLOWED"
                    st.markdown(
                        f"<div class='tool-msg'>⚠️ <b>{ts}</b> — critical: "
                        f"<span class='{color}'>{status}</span> | {e.get('action','')[:60]}</div>",
                        unsafe_allow_html=True,
                    )
                elif t == "llm_reply":
                    st.markdown(
                        f"<div class='jarvis-msg'>🤖 <b>{ts}</b> — llm: "
                        f"{e.get('input','')[:60]}</div>",
                        unsafe_allow_html=True,
                    )
    except Exception as exc:
        st.error(f"Could not load audit log: {exc}")

    # Auth panel
    st.markdown("---")
    st.markdown("**🔐 Authorization**")
    col1, col2 = st.columns(2)
    with col1:
        pin_input = st.text_input("Enter PIN to authorize", type="password", key="pin_auth")
        if st.button("🔓 Authorize with PIN") and pin_input:
            if engine.auth and engine.auth.verify_pin(pin_input):
                engine.auth.grant()
                st.success("Authorized for 30 seconds, Sir.")
            else:
                st.error("Incorrect PIN.")
    with col2:
        new_pin = st.text_input("Set new PIN (4-8 digits)", type="password", key="new_pin")
        if st.button("💾 Save PIN") and new_pin:
            if engine.auth:
                msg = engine.auth.set_pin(new_pin)
                st.success(msg)
