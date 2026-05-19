import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI  # <-- Zůstává standardní OpenAI klient

load_dotenv()

st.set_page_config(page_title="Bosch Bot s osobností", page_icon="🤖")
st.title("Bosch Bot")

# 1. Definice všech osobností, ze kterých půjde vybírat
OSOBNOSTI = {
    "🏴‍☠️ Pirátský kapitán": (
        "Jsi ostřílený mořský vlk a pirátský kapitán. Mluv drsně, používej pirátský slang "
        "(např. 'Do paromova!', 'U sta hromů!', 'suchozemská kryso'). Na každou otázku odpovídej "
        "s pirátským přizvukem, ale zároveň uživateli věcně a užitečně porď s projektem RBCB."
    ),
    "👔 Korporátní manažer": (
        "Jsi vysoce postavený manažer z korporátu Bosch. Tvůj projev je extrémně profesionální, "
        "škrobený a plný korporátního slangu (anglicismů), jako např. 'ASAP', 'fokusovat se', "
        "'synergie', 'vysyncovat se', 'KPIs'. Buď slušný, stručný a orientovaný na výkon."
    ),
    "☕ Naštvaný programátor": (
        "Jsi přepracovaný a cynický ajťák z Bosch, kterého neustále někdo otravuje blbými dotazy. "
        "Mluvíš trochu ironicky, stěžuješ si, že ti chladne kafe a že kód nikdo nečte. "
        "I přes své remcání ale nakonec technicky správně a přesně na otázku odpovíš."
    )
}

# 2. Výběr osobnosti v levém menu (přidán unikátní klíč 'key')
zvolena_osobnost = st.sidebar.selectbox("Vyber osobnost bota:", list(OSOBNOSTI.keys()), key="vyber_osobnosti")

# Pokud uživatel přepne osobnost, vymažeme starý chat a nastavíme nový System Prompt
if "aktualni_osobnost" not in st.session_state or st.session_state["aktualni_osobnost"] != zvolena_osobnost:
    st.session_state["aktualni_osobnost"] = zvolena_osobnost
    st.session_state.messages = [
        {
            "role": "system",
            "content": OSOBNOSTI[zvolena_osobnost]
        }
    ]

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

# Vykreslení historie chatu (přeskakujeme systémovou zprávu)
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Dynamické textové pole podle toho, kdo zrovna odpovídá
placeholder_text = "What is up?"
if "Pirátský" in zvolena_osobnost:
    placeholder_text = "Vyblej svůj dotaz sem, ty líná kůže..."
elif "Manažer" in zvolena_osobnost:
    placeholder_text = "Zadejte prosím váš dotaz pro optimalizaci procesů..."
elif "programátor" in zvolena_osobnost:
    placeholder_text = "Zase otravuješ? Co nefunguje?..."

if prompt := st.chat_input(placeholder_text):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})