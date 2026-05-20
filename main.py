import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI

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


# ___________________

st.title("Bosch bot")

if "messages" not in st.session_state:
    st.session_state.messages = []

user_input = st.text_input("Zadej otázku pro Bosch bota:")

if user_input:
    st.session_state.messages.append(
        f"Vaše otázka: {user_input}")
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
    st.session_state.messages.append(
        f"Bosch bot: {response}")


for message in st.session_state.messages:
    st.write(message)
