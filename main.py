import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
#from pages import logs

st.set_page_config(page_title="Úvodní strana")

load_dotenv()

endpoint = "https://budwise-brigadnici-resource.openai.azure.com/openai/v1"
deployment_name = "gpt-5"
api_key = os.getenv("AZURE_OPENAI_API_KEY")

print("API key se načetl:", api_key is not None)
client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)

# ___________________
st.title("Bosch bot")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie zpráv
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Vstup od uživatele
user_input = st.chat_input("Zadej otázku pro Bosch bota:")

if user_input:
    # Přidání zprávy uživatele do historie
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Generování odpovědi
    completion = client.chat.completions.create(
        model=deployment_name,
        messages=st.session_state.messages
    )
    
    response = completion.choices[0].message.content
    
    # Přidání odpovědi asistenta do historie
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)