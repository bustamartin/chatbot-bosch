import os
import re
import math
import base64
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from io import BytesIO

# 1. Nastavení vzhledu stránky
st.set_page_config(page_title="AI G-code asistent", layout="wide", page_icon="🛠️")
st.title("🛠️ AI G-code asistent")

# 2. Načtení API klíče a konfigurace OpenAI klienta
load_dotenv()
ENDPOINT = "https://budwise-brigadnici-resource.openai.azure.com/openai/v1"
DEPLOYMENT_NAME = "gpt-5"  # GPT pro text
IMAGE_DEPLOYMENT_NAME = "gpt-image-1-mini"  # DALL-E pro obrázky
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
API_VERSION = "2025-04-01-preview"

client = OpenAI(base_url=ENDPOINT, api_key=API_KEY)


# 3. Pomocná funkce: Parsování G-codu
def parse_gcode_to_dataframe(file_content):
    lines = file_content.decode("utf-8", errors="ignore").splitlines()
    x_coords, y_coords, line_numbers = [], [], []
    current_x, current_y = 0.0, 0.0
    current_feedrate = 1200.0
    total_time_minutes = 0.0
    warnings = []

    x_pattern = re.compile(r'X\s*(-?\d+\.?\d*)', re.IGNORECASE)
    y_pattern = re.compile(r'Y\s*(-?\d+\.?\d*)', re.IGNORECASE)
    f_pattern = re.compile(r'F\s*(\d+\.?\d*)', re.IGNORECASE)

    for idx, line in enumerate(lines):
        line_num = idx + 1
        clean_line = line.split(';')[0]
        if "G0" in clean_line.upper() or "G1" in clean_line.upper():
            match_x = x_pattern.search(clean_line)
            match_y = y_pattern.search(clean_line)
            match_f = f_pattern.search(clean_line)

            if match_f:
                current_feedrate = float(match_f.group(1))
                if current_feedrate > 6000:
                    warnings.append(f"Line {line_num}: ⚠️ Extrémně vysoká rychlost posuvu (F={current_feedrate}).")
                if current_feedrate <= 0: current_feedrate = 1200.0

            if match_x or match_y:
                next_x = float(match_x.group(1)) if match_x else current_x
                next_y = float(match_y.group(1)) if match_y else current_y
                distance = math.sqrt((next_x - current_x) ** 2 + (next_y - current_y) ** 2)
                if "G0" in clean_line.upper() and distance > 100:
                    warnings.append(f"Line {line_num}: 🚧 Dlouhý rychlý přejezd (G0).")
                if distance > 0: total_time_minutes += distance / current_feedrate
                current_x, current_y = next_x, next_y
                x_coords.append(current_x);
                y_coords.append(current_y);
                line_numbers.append(line_num)

    # Analýza ostrých úhlů
    for i in range(1, len(x_coords) - 1):
        v1 = (x_coords[i] - x_coords[i - 1], y_coords[i] - y_coords[i - 1])
        v2 = (x_coords[i + 1] - x_coords[i], y_coords[i + 1] - y_coords[i])
        l1, l2 = math.sqrt(v1[0] ** 2 + v1[1] ** 2), math.sqrt(v2[0] ** 2 + v2[1] ** 2)
        if l1 > 0 and l2 > 0:
            cos_a = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))
            if math.degrees(math.acos(cos_a)) > 135:
                warnings.append(f"Line {line_numbers[i]}: 📉 Ostrá změna směru.")

    df = pd.DataFrame(
        {'Krok': range(1, len(x_coords) + 1), 'X': x_coords, 'Y': y_coords, 'Řádek v G-code': line_numbers})
    return df, lines, total_time_minutes, warnings


# 4. UI Rozhraní
uploaded_file = st.file_uploader("Nahraj svůj G-code soubor", type=["gcode", "nc", "txt"])

if uploaded_file is not None:
    # Reset při změně souboru
    if "aktualni_soubor" not in st.session_state or st.session_state["aktualni_soubor"] != uploaded_file.name:
        st.session_state["aktualni_soubor"] = uploaded_file.name
        for key in ["ai_popis", "messages", "generated_img_base64"]:
            if key in st.session_state: del st.session_state[key]

    file_bytes = uploaded_file.read()
    df, raw_lines, odhadovany_cas_minuty, bezpecnostni_varovani = parse_gcode_to_dataframe(file_bytes)

    if not df.empty:
        # Čistění a příprava ořezaného vzorku kódu (vymazání komentářů a mezer pro úsporu tokenů)
        ciste_radky = [line.strip().split(';')[0] for line in raw_lines if line.strip()]
        ciste_radky = [line for line in ciste_radky if line]

        if len(ciste_radky) > 40:
            vzorek_kodu = "\n".join(ciste_radky[:20]) + "\n... [kráceno] ...\n" + "\n".join(ciste_radky[-20:])
        else:
            vzorek_kodu = "\n".join(ciste_radky)

        col1, col2 = st.columns([3, 2])

        # --- LEVÝ SLOUPCE: Statistiky, Tabulka a OBRÁZEK ---
        with col1:
            st.subheader("📊 Statistiky drah")
            sirka, vyska = df['X'].max() - df['X'].min(), df['Y'].max() - df['Y'].min()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Počet pohybů", f"{len(df)} x")
            m2.metric("Šířka (X)", f"{sirka:.1f} mm")
            m3.metric("Výška (Y)", f"{vyska:.1f} mm")
            m4.metric("Odhadovaný čas",
                      f"{int(odhadovany_cas_minuty)}m" if odhadovany_cas_minuty > 1 else f"{int(odhadovany_cas_minuty * 60)}s")

            st.subheader("📋 Tabulka souřadnic")
            st.dataframe(df, use_container_width=True, height=300)

            # --- OBRÁZEK: Vizualizace drah ---
            st.write("---")
            st.subheader("🖼️ AI Vizualizace drah")
            if "generated_img_base64" not in st.session_state:
                with st.spinner("Generuji vizualizační model součástky..."):
                    try:
                        base_path = f'openai/deployments/{IMAGE_DEPLOYMENT_NAME}/images'
                        gen_url = f"https://budwise-brigadnici-resource.cognitiveservices.azure.com/{base_path}/generations?api-version={API_VERSION}"

                        body = {
                            "prompt": f"Realistic technical engineering isometric visualization of CNC toolpaths for this G-code:\n{vzorek_kodu}",
                            "n": 1, "size": "1024x1024", "quality": "medium", "output_format": "png"
                        }

                        resp = requests.post(gen_url, headers={'Api-Key': API_KEY, 'Content-Type': 'application/json'},
                                             json=body).json()
                        st.session_state["generated_img_base64"] = resp['data'][0]['b64_json']
                    except Exception as e:
                        st.error(f"Chyba při generování obrázku: {e}")

            if "generated_img_base64" in st.session_state:
                img_bytes = base64.b64decode(st.session_state["generated_img_base64"])
                st.image(img_bytes, caption="Předpokládaný tvar na základě G-codu", use_container_width=True)

        # --- PRAVÝ SLOUPCE: Popis, Rizika a Chat ---
        with col2:
            st.subheader("🤖 AI popis")
            if "ai_popis" not in st.session_state:
                with st.spinner("Studuji kód..."):
                    prompt = (
                        "Jsi odborný asistent a expert na CNC frézování a 3D tisk. "
                        "Tvým úkolem je analyzovat poskytnutý vzorek G-codu.\n\n"
                        "STRIKTNÍ PRAVIDLO: Neříkej, co kód NENÍ.\n"
                        "1. Hned v první větě přímo věcně pojmenuj technologii, o kterou se jedná.\n"
                        "2. Popiš, jak bude hotový produkt podle těchto drah přibližně vypadat (tvar, geometrie).\n"
                        "3. Stručně vysvětli, co přesně stroj v tomto výseku dělá a jaké příkazy používá.\n\n"
                        f"G-CODE VZOREK:\n{vzorek_kodu}"
                    )
                    try:
                        comp = client.chat.completions.create(
                            model=DEPLOYMENT_NAME,
                            messages=[{"role": "user", "content": prompt}],
                            timeout=60.0,
                            max_completion_tokens=1000  # Zvýšeno pro jistotu kompletního popisu
                        )
                        st.session_state["ai_popis"] = comp.choices[0].message.content
                    except Exception as e:
                        st.session_state["ai_popis"] = f"⚠️ Došlo k chybě při komunikaci s AI: {e}"

            st.info(st.session_state["ai_popis"])

            st.subheader("⚠️ Rizikové pohyby")
            if bezpecnostni_varovani:
                st.warning(f"Nalezeno {len(bezpecnostni_varovani)} rizik:")
                for v in bezpecnostni_varovani[:3]: st.write(v)
            else:
                st.success("🚀 Žádná rizika nebyla detekována.")

            st.write("---")
            st.subheader("💬 Konzultace s AI")

            # Inicializace zpráv a základního systémového promptu
            if "messages" not in st.session_state:
                system_prompt = f"Jsi CNC asistent. Vycházej věcně z této analýzy: {st.session_state['ai_popis']}"
                st.session_state.messages = [{"role": "system", "content": system_prompt}]

            # Vykreslení historie chatu z session_state
            chat_container = st.container(height=350)
            with chat_container:
                for m in st.session_state.messages:
                    if m["role"] != "system":
                        with st.chat_message(m["role"]):
                            st.markdown(m["content"])

            # Zpracování nového vstupu od uživatele
            if chat_prompt := st.chat_input("Zeptejte se na detaily součástky..."):
                # 1. Okamžité uložení a zobrazení dotazu uživatele
                st.session_state.messages.append({"role": "user", "content": chat_prompt})
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(chat_prompt)

                    # 2. Generování odpovědi bez streamování, aby nedocházelo k chybám v Azure
                    with st.chat_message("assistant"):
                        with st.spinner("Přemýšlím..."):
                            try:
                                response_completion = client.chat.completions.create(
                                    model=DEPLOYMENT_NAME,
                                    messages=st.session_state.messages,
                                    stream=False,  # Vypnuto streamování pro maximální stabilitu v Azure
                                    max_completion_tokens=2000
                                    # Navýšený limit pro dlouhé odpovědi (máte k dispozici 5000)
                                )
                                response = response_completion.choices[0].message.content
                                st.markdown(response)
                            except Exception as e:
                                response = f"⚠️ Nepodařilo se získat odpověď z Azure OpenAI: {e}"
                                st.error(response)

                # 3. Uložení odpovědi asistenta do historie a následný čistý restart stránky
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()
    else:
        st.warning("V souboru nebyly nalezeny žádné platné pohyby.")