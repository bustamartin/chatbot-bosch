import os
import re
import math
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# 1. Nastavení vzhledu stránky
st.set_page_config(page_title="AI G-code asistent", layout="wide")
st.title("🛠️ AI G-code asistent")

# 2. Načtení API klíče a konfigurace OpenAI klienta
load_dotenv()
ENDPOINT = "https://budwise-brigadnici-resource.openai.azure.com/openai/v1"
DEPLOYMENT_NAME = "gpt-5"  # Ujistěte se, že toto odpovídá názvu vašeho nasazení v Azure
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

client = OpenAI(base_url=ENDPOINT, api_key=API_KEY)


# 3. Pomocná funkce: Parsování G-codu a výpočet statistik
def parse_gcode_to_dataframe(file_content):
    lines = file_content.decode("utf-8", errors="ignore").splitlines()

    x_coords = []
    y_coords = []
    current_x, current_y = 0.0, 0.0
    current_feedrate = 1200.0  # Výchozí rychlost (mm/min)
    total_time_minutes = 0.0

    # Regulární výrazy pro vytažení X, Y a rychlosti F
    x_pattern = re.compile(r'X\s*(-?\d+\.?\d*)', re.IGNORECASE)
    y_pattern = re.compile(r'Y\s*(-?\d+\.?\d*)', re.IGNORECASE)
    f_pattern = re.compile(r'F\s*(\d+\.?\d*)', re.IGNORECASE)

    for line in lines:
        clean_line = line.split(';')[0]  # Ignorujeme komentáře

        if "G0" in clean_line.upper() or "G1" in clean_line.upper():
            match_x = x_pattern.search(clean_line)
            match_y = y_pattern.search(clean_line)
            match_f = f_pattern.search(clean_line)

            # Pokud řádek mění rychlost posuvu
            if match_f:
                current_feedrate = float(match_f.group(1))
                if current_feedrate <= 0:
                    current_feedrate = 1200.0

            # Zaneseme bod, pokud se mění X nebo Y koordinát
            if match_x or match_y:
                next_x = float(match_x.group(1)) if match_x else current_x
                next_y = float(match_y.group(1)) if match_y else current_y

                # Výpočet vzdálenosti (v mm) mezi starým a novým bodem
                distance = math.sqrt((next_x - current_x) ** 2 + (next_y - current_y) ** 2)
                if distance > 0:
                    total_time_minutes += distance / current_feedrate

                # Aktualizace pozice
                current_x = next_x
                current_y = next_y
                x_coords.append(current_x)
                y_coords.append(current_y)

    df = pd.DataFrame({'X': x_coords, 'Y': y_coords})
    return df, lines, total_time_minutes


# 4. UI Rozhraní ve Streamlitu
uploaded_file = st.file_uploader("Nahraj svůj G-code soubor (.gcode, .nc, .txt)", type=["gcode", "nc", "txt"])

if uploaded_file is not None:
    file_bytes = uploaded_file.read()

    # Zpracování souboru
    df, raw_lines, odhadovany_cas_minuty = parse_gcode_to_dataframe(file_bytes)

    if not df.empty:
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("📊 Statistiky a vizualizace drah")
            pocet_pohybu = len(df)
            min_x, max_x = df['X'].min(), df['X'].max()
            min_y, max_y = df['Y'].min(), df['Y'].max()
            sirka, vyska = max_x - min_x, max_y - min_y

            # Formátování času na minuty a sekundy (nebo hodiny)
            if odhadovany_cas_minuty < 1:
                cas_vypis = f"{int(odhadovany_cas_minuty * 60)} s"
            elif odhadovany_cas_minuty > 60:
                cas_vypis = f"{int(odhadovany_cas_minuty // 60)}h {int(odhadovany_cas_minuty % 60)}m"
            else:
                cas_vypis = f"{int(odhadovany_cas_minuty)}m {int((odhadovany_cas_minuty % 1) * 60)}s"

            # Zobrazení statistik
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Počet pohybů", f"{pocet_pohybu} x")
            m2.metric("Šířka (X)", f"{sirka:.1f} mm")
            m3.metric("Výška (Y)", f"{vyska:.1f} mm")
            m4.metric("Odhadovaný čistý čas", cas_vypis)

            if sirka > 300 or vyska > 300:
                st.error("⚠️ Varování: Rozměry přesahují běžnou pracovní plochu (300 mm)!")
            else:
                st.success("✅ Rozměry jsou v pořádku pro standardní stroje.")

            st.caption("Trajektorie pohybu nástroje (X/Y):")
            st.line_chart(df, x="X", y="Y")

            # Přehledná tabulka se souřadnicemi
            st.subheader("📋 Tabulka souřadnic (Pandas DataFrame)")
            st.dataframe(df, use_container_width=True)

        with col2:
            # Přejmenováno na AI popis podle zadání
            st.subheader("🤖 AI popis")

            # Příprava zkráceného vzorku pro AI
            if len(raw_lines) > 60:
                vzorek_kodu = "\n".join(raw_lines[:30]) + "\n... [kráceno] ...\n" + "\n".join(raw_lines[-30:])
            else:
                vzorek_kodu = "\n".join(raw_lines)

            # Upravený profesionální prompt bez jakéhokoliv vlastního jména
            prompt = (
                "Jsi odborný asistent a expert na CNC frézování a 3D tisk. "
                "Tvým úkolem je analyzovat poskytnutý vzorek G-codu. "
                "STRIKTNÍ PRAVIDLO: Neříkej, co kód NENÍ (např. 'Tento kód neobsahuje frézování'). "
                "Hned v první větě přímo věcně pojmenuj technologii, o kterou se jedná (např. 'Jedná se o 3D tisk objektu...' nebo 'Tento program provádí frézování kapsy...'). "
                "Následně lidskou řečí a česky stručně vysvětli, co přesně stroj v tomto výseku dělá a jaké příkazy používá.\n\n"
                f"G-CODE VZOREK:\n{vzorek_kodu}"
            )

            with st.spinner("AI studuje kód..."):
                try:
                    completion = client.chat.completions.create(
                        model=DEPLOYMENT_NAME,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.info(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"Chyba při volání AI: {e}")
    else:
        st.warning("V souboru nebyly nalezeny žádné platné pohyby G0/G1.")