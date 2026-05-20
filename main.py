import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
import sqlite3

from pages import logs

load_dotenv()

endpoint = "https://budwise-brigadnici-resource.openai.azure.com/openai/v1"
deployment_name = "gpt-5"
api_key = os.getenv("AZURE_OPENAI_API_KEY")

print("API key se načetl:", api_key is not None)

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)

# Inicializace sqlite databáze (vytvoří soubor data.db v kořeni projektu)
def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_webs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma TEXT,
            obor TEXT,
            styl TEXT,
            slovo1 TEXT,
            slovo2 TEXT,
            text_kod TEXT,
            vytvoreno TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# UI Aplikace (streamlit)

st.title("🤖 AI Generator Landing Pages")
st.write("Zadejte parametry a AI vám vytvoří kompletní prodejní stránku na míru.")

# Formulář pro uživatele
with st.form("generator_form"):
    firma = st.text_input("Název firmy:", placeholder="např. Káva z hor s.r.o.")
    obor = st.text_input("Obor podnikání:", placeholder="např. Výběrová kávová zrna, pražírna")
    styl = st.selectbox(
        "Styl a atmosféra webu:",
        ["Moderní a čistý (SaaS)", "Luxusní a elegantní", "Technologický a tmavý", "Hravý a barevný"]
    )
    
    submit_button = st.form_submit_button("Vygenerovat web")
