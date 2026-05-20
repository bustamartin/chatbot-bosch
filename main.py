import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI
<<<<<<< HEAD
import sqlite3
from generator import vygeneruj_web
# from pages import logs  # Zakomentuj, pokud soubor ještě nemáš
=======

st.set_page_config(
    page_title="Úvodní strana"
)
>>>>>>> 11755e421bcbadb8d8ce7c299bea36729fe6b832

load_dotenv()

# Konfigurace Azure OpenAI
endpoint = "https://budwise-brigadnici-resource.openai.azure.com/openai/v1"
deployment_name = "gpt-5"
api_key = os.getenv("AZURE_OPENAI_API_KEY")

<<<<<<< HEAD
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
=======
client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)

st.title("Bosch bot")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

user_input = st.chat_input("Zadej otázku pro Bosch bota:")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.write(user_input)

    completion = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {
                "role": "user",
                "content": user_input,
            }
        ],
    )

    response = completion.choices[0].message.content

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

    with st.chat_message("assistant"):
        st.write(response)
>>>>>>> 11755e421bcbadb8d8ce7c299bea36729fe6b832
