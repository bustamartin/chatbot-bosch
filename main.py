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


# 3. Pomocná funkce: Parsování G-codu, výpočet času a bezpečnostní audit
def parse_gcode_to_dataframe(file_content):
    lines = file_content.decode("utf-8", errors="ignore").splitlines()

    x_coords = []
    y_coords = []
    line_numbers = []

    current_x, current_y = 0.0, 0.0
    current_feedrate = 1200.0
    total_time_minutes = 0.0

    # Seznam pro ukládání bezpečnostních varování (rizikových pohybů)
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

            # --- RIZIKO 1: Kontrola extrémní rychlosti (Feedrate) ---
            if match_f:
                current_feedrate = float(match_f.group(1))
                if current_feedrate > 6000:
                    warnings.append(
                        f"Line {line_num}: ⚠️ Extrémně vysoká rychlost posuvu (F={current_feedrate} mm/min). Hrozí zlomení nástroje!")
                if current_feedrate <= 0:
                    current_feedrate = 1200.0

            if match_x or match_y:
                next_x = float(match_x.group(1)) if match_x else current_x
                next_y = float(match_y.group(1)) if match_y else current_y

                distance = math.sqrt((next_x - current_x) ** 2 + (next_y - current_y) ** 2)

                # --- RIZIKO 2: Kontrola nebezpečných rychlých přejezdů G0 ---
                if "G0" in clean_line.upper() and distance > 100:
                    warnings.append(
                        f"Line {line_num}: 🚧 Dlouhý rychlý přejezd (G0) o délce {distance:.1f} mm. Prověř, zda nehrozí kolize s upínkami.")

                if distance > 0:
                    total_time_minutes += distance / current_feedrate

                current_x = next_x
                current_y = next_y

                x_coords.append(current_x)
                y_coords.append(current_y)
                line_numbers.append(line_num)

    # --- RIZIKO 3: Ostré změny směru (úhly) ---
    for i in range(1, len(x_coords) - 1):
        x1, y1 = x_coords[i - 1], y_coords[i - 1]
        x2, y2 = x_coords[i], y_coords[i]
        x3, y3 = x_coords[i + 1], y_coords[i + 1]

        v1 = (x2 - x1, y2 - y1)
        v2 = (x3 - x2, y3 - y2)

        len_v1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
        len_v2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

        if len_v1 > 0 and len_v2 > 0:
            dot_product = v1[0] * v2[0] + v1[1] * v2[1]
            cos_angle = max(-1.0, min(1.0, dot_product / (len_v1 * len_v2)))
            angle_rad = math.acos(cos_angle)
            angle_deg = math.degrees(angle_rad)

            if angle_deg > 135:
                warnings.append(
                    f"Line {line_numbers[i]}: 📉 Velmi ostrá změna směru ({angle_deg:.1f}°). Může způsobit vibrace nebo poškodit povrch.")

    df = pd.DataFrame({
        'Krok': range(1, len(x_coords) + 1),
        'X': x_coords,
        'Y': y_coords,
        'Řádek v G-code': line_numbers
    })
    return df, lines, total_time_minutes, warnings


# 4. UI Rozhraní ve Streamlitu
uploaded_file = st.file_uploader("Nahraj svůj G-code soubor (.gcode, .nc, .txt)", type=["gcode", "nc", "txt"])

if uploaded_file is not None:
    file_bytes = uploaded_file.read()

    # Zpracování souboru
    df, raw_lines, odhadovany_cas_minuty, bezpecnostni_varovani = parse_gcode_to_dataframe(file_bytes)

    if not df.empty:
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("📊 Statistiky drah")
            pocet_pohybu = len(df)
            min_x, max_x = df['X'].min(), df['X'].max()
            min_y, max_y = df['Y'].min(), df['Y'].max()
            sirka, vyska = max_x - min_x, max_y - min_y

            # Formátování času
            if odhadovany_cas_minuty < 1:
                cas_vypis = f"{int(odhadovany_cas_minuty * 60)} s"
            elif odhadovany_cas_minuty > 60:
                cas_vypis = f"{int(odhadovany_cas_minuty // 60)}h {int(odhadovany_cas_minuty % 60)}m"
            else:
                cas_vypis = f"{int(odhadovany_cas_minuty)}m {int((odhadovany_cas_minuty % 1) * 60)}s"

            # Zobrazení základních statistik
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Počet pohybů", f"{pocet_pohybu} x")
            m2.metric("Šířka (X)", f"{sirka:.1f} mm")
            m3.metric("Výška (Y)", f"{vyska:.1f} mm")
            m4.metric("Odhadovaný čistý čas", cas_vypis)

            if sirka > 300 or vyska > 300:
                st.error("⚠️ Varování: Rozměry přesahují běžnou pracovní plochu (300 mm)!")
            else:
                st.success("✅ Rozměry jsou v pořádku pro standardní stroje.")

            # Přehledná tabulka se souřadnicemi
            st.subheader("📋 Tabulka souřadnic (Pandas DataFrame)")
            st.dataframe(df, use_container_width=True)

        with col2:
            st.subheader("🤖 AI popis")

            # Příprava zkráceného vzorku pro AI
            if len(raw_lines) > 60:
                vzorek_kodu = "\n".join(raw_lines[:30]) + "\n... [kráceno] ...\n" + "\n".join(raw_lines[-30:])
            else:
                vzorek_kodu = "\n".join(raw_lines)

            prompt = (
                "Jsi odborný asistent a expert na CNC frézování a 3D tisk. "
                "Tvým úkolem je analyzovat poskytnutý vzorek G-codu.\n\n"
                "STRIKTNÍ PRAVIDLO: Neříkej, co kód NENÍ.\n"
                "1. Hned v první větě přímo věcně pojmenuj technologii, o kterou se jedná.\n"
                "2. Popiš, jak bude hotový produkt podle těchto drah přibližně vypadat (tvar, geometrie).\n"
                "3. Stručně vysvětli, co přesně stroj v tomto výseku dělá a jaké příkazy používá.\n\n"
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

            # --- SEKCE: RIZIKOVÉ POHYBY (BEZPEČNOSTNÍ AUDIT) ---
            st.subheader("⚠️ Rizikové pohyby")
            if bezpecnostni_varovani:
                st.warning(f"V kódu bylo nalezeno {len(bezpecnostni_varovani)} potenciálních rizik:")
                for varovani in bezpecnostni_varovani[:10]:
                    st.write(varovani)
                if len(bezpecnostni_varovani) > 10:
                    st.info(f"...a dalších {len(bezpecnostni_varovani) - 10} varování.")
            else:
                st.success(
                    "🚀 Žádné kritické nebo nebezpečné trajektorie nebyly matematickou analýzou detekovány. Kód vypadá stabilně.")

    else:
        st.warning("V souboru nebyly nalezeny žádné platné pohyby G0/G1.")