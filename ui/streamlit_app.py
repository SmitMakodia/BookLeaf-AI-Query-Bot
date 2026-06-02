import streamlit as st
import httpx
import sqlite3
import pandas as pd

st.set_page_config(page_title="BookLeaf AI Demo", layout="wide")

st.markdown("""
<style>
.small-font { font-size: 0.85rem; }
.metric-container { background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

st.title("BookLeaf AI — Automation Demo")
st.markdown("This dashboard is designed to test the **Customer Query Bot** and **Identity Unification System** assignments.")

col_left, col_right = st.columns([1, 2])

def load_db_data():
    conn = sqlite3.connect("bookleaf.db")
    authors = pd.read_sql_query("SELECT id, name, email FROM authors", conn)
    books = pd.read_sql_query("SELECT author_id, book_title, royalty_status, book_live_date FROM books", conn)
    platforms = pd.read_sql_query("SELECT author_id, platform, identifier FROM platform_identifiers", conn)
    conn.close()
    return authors, books, platforms

try:
    df_authors, df_books, df_platforms = load_db_data()
except Exception:
    df_authors, df_books, df_platforms = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

with col_left:
    st.subheader("1. Persona & Database View")
    st.markdown("Select a persona to simulate a query from different channels.")
    
    persona = st.selectbox(
        "Simulate As:", 
        options=[
            "Sara Johnson (Instagram)", 
            "Sara Johnson (Email)",
            "John Doe (WhatsApp)",
            "Unknown User (Email)"
        ]
    )

    if persona == "Sara Johnson (Instagram)":
        platform = "instagram"
        identifier = "@sarapoetry23"
        display_author = "Sara Johnson"
    elif persona == "Sara Johnson (Email)":
        platform = "email"
        identifier = "sara.johnson@xyz.com"
        display_author = "Sara Johnson"
    elif persona == "John Doe (WhatsApp)":
        platform = "whatsapp"
        identifier = "+1234567890"
        display_author = "John Doe"
    else:
        platform = "email"
        identifier = "unknown@email.com"
        display_author = "None"

    st.info(f"**Channel:** `{platform}`\n\n**Identifier:** `{identifier}`")

    with st.expander("🔍 View Internal Supabase (Mock DB)"):
        if not df_authors.empty:
            st.markdown("**Authors Table**")
            st.dataframe(df_authors, hide_index=True)
            st.markdown("**Books Table**")
            st.dataframe(df_books, hide_index=True)
            st.markdown("**Platform Identifiers Table**")
            st.dataframe(df_platforms, hide_index=True)
        else:
            st.warning("Database not seeded yet. Please start the backend.")

    st.subheader("2. Test Queries")
    st.markdown("Click a query below to instantly send it to the AI.")
    
    queries = [
        "Is my book live yet?",
        "When will I get my royalty?",
        "Where is my author copy?",
        "What is the Bestseller Package?",
        "Can you publish my new book?"
    ]
    
    selected_query = None
    for q in queries:
        if st.button(q, use_container_width=True):
            selected_query = q
            
    custom_query = st.chat_input("Or type a custom query here...")
    if custom_query:
        selected_query = custom_query

with col_right:
    st.subheader("3. AI Execution & Routing Logs")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if selected_query:
        st.session_state.chat_history.append({"role": "user", "content": selected_query})
        
        with st.spinner("AI is processing..."):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        "http://127.0.0.1:8000/api/v1/chat",
                        json={"query": selected_query, "channel": platform, "identifier": identifier},
                    )
                    response.raise_for_status()
                    result = response.json()
            except Exception as e:
                result = {"response": f"Error: {str(e)}", "escalated": True, "confidence": 0.0, "sources": [], "intent": "ERROR", "identity_confidence": 0.0}

        st.session_state.chat_history.append({"role": "assistant", "content": result})

    for i, msg in enumerate(st.session_state.chat_history):
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            res = msg["content"]
            with st.chat_message("assistant"):
                st.write(res.get("response", ""))
                
                m1, m2, m3, m4 = st.columns(4)
                
                conf = res.get("confidence", 0.0)
                escalated = res.get("escalated", False)
                ident_conf = res.get("identity_confidence", 0.0)
                intent = res.get("intent", "UNKNOWN")
                
                if ident_conf == 1.0:
                    ident_method = "Exact (DB)"
                elif ident_conf > 0:
                    ident_method = "Fuzzy/Graph"
                else:
                    ident_method = "Unresolved"
                
                m1.metric("Intent Detected", intent)
                m2.metric("Identity Match", ident_method, f"{ident_conf:.0%}")
                
                if escalated:
                    m3.metric("Escalated to Human", "YES", "- Low Confidence", delta_color="inverse")
                    m4.metric("Overall Confidence", f"{conf:.0%}", "Needs Review", delta_color="inverse")
                else:
                    m3.metric("Escalated to Human", "NO", "+ Auto-Resolved", delta_color="normal")
                    m4.metric("Overall Confidence", f"{conf:.0%}", "High", delta_color="normal")
                
                sources = res.get("sources", [])
                if sources:
                    with st.expander("View Retrieved Context Sources"):
                        for s in sources:
                            st.caption(f"`{s}`")
