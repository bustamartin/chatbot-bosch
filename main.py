import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI
import sqlite3
from generator import vygeneruj_web
# from pages import logs  # Zakomentuj, pokud soubor ještě nemáš

load_dotenv()

# Konfigurace Azure OpenAI
endpoint = "https://budwise-brigadnici-resource.openai.azure.com/openai/v1"
deployment_name = "gpt-5"
api_key = os.getenv("AZURE_OPENAI_API_KEY")

client = 

# Inicializace databáze
def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_webs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma TEXT, obor TEXT, styl TEXT, 
            vysledek_ai TEXT, vytvoreno TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

st.title("🤖 AI Generator Landing Pages")

with st.form("generator_form"):
    firma = st.text_input("Název firmy:")
    obor = st.text_input("Obor podnikání:")
    styl = st.selectbox("Styl:", ["Moderní", "Luxusní", "Technologický", "Hravý"])
    submit_button = st.form_submit_button("Vygenerovat web")

if submit_button:
    with st.spinner("AI generuje..."):
        # Zavolání generátoru
        vysledek = vygeneruj_web(firma, obor, styl, client, deployment_name)
        st.write(vysledek)
        
        # Uložení do DB
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO generated_webs (firma, obor, styl, vysledek_ai) VALUES (?,?,?,?)", 
                       (firma, obor, styl, vysledek))
        conn.commit()
        conn.close()
        st.success("Web vygenerován a uložen do databáze!")