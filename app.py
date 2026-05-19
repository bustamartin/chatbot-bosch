import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI  # <-- Zůstává standardní OpenAI klient

load_dotenv()

st.title("ChatGPT-like clone")

# Nastavení názvu vašeho modelu/deploymentu v Azure
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-5"

# Pro standardní OpenAI klienta musíme URL poskládat ručně včetně verze API
deployment_name = st.session_state["openai_model"]
endpoint = "https://budwise-brigadnici-resource.openai.azure.com/openai/v1"
api_version = "2024-02-15-preview"

# Inicializace klienta pomocí base_url
client = OpenAI(
    base_url=endpoint,
    api_key=os.getenv("AZURE_OPENAI_API_KEY")
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=deployment_name,  # Azure toto v těle požadavku sice ignoruje (bere to z URL), ale parametr je pro knihovnu povinný
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})