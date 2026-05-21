import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
import sqlite3
from io import StringIO
import json
import random

load_dotenv()

endpoint = "https://budwise-brigadnici-resource.openai.azure.com/openai/v1"
deployment_name = "gpt-5"
api_key = os.getenv("AZURE_OPENAI_API_KEY")

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
    timeout=90.0,
)

st.set_page_config(
    page_title="Logy",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Martin – AI Security & Log Analyzer")

uploaded_file = st.file_uploader("Nahraj CSV soubor s logy", type=["csv"])
generate_ai_logs = st.button("Vygenerovat AI testovací logy")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

elif generate_ai_logs:
    try:
        with st.spinner("AI generuje scénář logů..."):
            completion = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": """
                        Jsi generátor bezpečnostních scénářů.
                        Vrať pouze čistý JSON bez markdownu.
                        JSON musí obsahovat pole scenarios.
                        Každý scénář má:
                        event, ip, url, user_agent, count.

                        Povolené eventy:
                        failed_login, success_login, request, port_scan
                        """
                    },
                    {
                        "role": "user",
                        "content": """
                        Vygeneruj 8 realistických security scénářů.
                        Některé mají být podezřelé.
                        Count dej mezi 2 až 8.
                        """
                    }
                ],
                max_completion_tokens=1200,
                reasoning_effort="minimal",
                timeout=120,
            )

            json_content = completion.choices[0].message.content

            if not json_content:
                st.error("AI vrátila prázdnou odpověď.")
                st.write(completion)
                st.stop()

            json_content = json_content.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_content)

            fake_logs = []

            for scenario in data["scenarios"]:
                for i in range(int(scenario["count"])):
                    fake_logs.append({
                        "event": scenario["event"],
                        "ip": scenario["ip"],
                        "url": scenario["url"],
                        "user_agent": scenario["user_agent"]
                    })

            df = pd.DataFrame(fake_logs)

            st.success("AI vygenerovala testovací logy.")
            st.dataframe(df)

    except Exception as e:
        st.error("Generování AI logů se nepovedlo.")
        st.code(str(e))
        st.stop()

else:
    st.info("Nahraj CSV soubor nebo vygeneruj AI testovací logy.")
    st.stop()

required_columns = ["event", "ip", "url"]
missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    st.error(f"CSV soubor nemá potřebné sloupce: {missing_columns}")
    st.stop()

conn = sqlite3.connect("security_logs.db")
df.to_sql("logs", conn, if_exists="replace", index=False)
conn.close()

failed_logins = df[df["event"] == "failed_login"]
failed_by_ip = failed_logins["ip"].value_counts()
suspicious_failed_logins = failed_by_ip[failed_by_ip >= 3]

requests_by_ip = df["ip"].value_counts()
suspicious_many_requests = requests_by_ip[requests_by_ip >= 5]

dangerous_urls = [
    "/admin", "/wp-admin", "/phpmyadmin", "/.env",
    "/etc/passwd", "/config.php", "/backup.zip", "/db.sql"
]
suspicious_urls = df[df["url"].isin(dangerous_urls)]

port_scans = df[df["event"] == "port_scan"]
port_scans_by_ip = port_scans["ip"].value_counts()
suspicious_port_scans = port_scans_by_ip[port_scans_by_ip >= 3]

st.subheader("1. Více failed loginů")
st.write(suspicious_failed_logins)

st.subheader("2. Mnoho requestů z jedné IP")
st.write(suspicious_many_requests)

st.subheader("3. Podezřelé URL")
st.write(suspicious_urls)

st.subheader("4. Scanování portů")
st.write(suspicious_port_scans)

report = f"""
Security report:

1. Více failed loginů:
{suspicious_failed_logins.to_string()}

2. Mnoho requestů z jedné IP:
{suspicious_many_requests.to_string()}

3. Podezřelé URL:
{suspicious_urls.to_string(index=False)}

4. Scanování portů:
{suspicious_port_scans.to_string()}
"""

html_report = f"""
<html>
<head>
    <meta charset="UTF-8">
    <title>Security report</title>
</head>
<body>
    <h1>Security report</h1>

    <h2>1. Více failed loginů</h2>
    <pre>{suspicious_failed_logins.to_string()}</pre>

    <h2>2. Mnoho requestů z jedné IP</h2>
    <pre>{suspicious_many_requests.to_string()}</pre>

    <h2>3. Podezřelé URL</h2>
    {suspicious_urls.to_html(index=False)}

    <h2>4. Scanování portů</h2>
    <pre>{suspicious_port_scans.to_string()}</pre>
</body>
</html>
"""

st.download_button(
    label="Stáhnout report jako HTML",
    data=html_report,
    file_name="security_report.html",
    mime="text/html"
)

if st.button("Vygenerovat AI security summary"):
    try:
        with st.spinner("AI analyzuje report..."):
            completion = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Jsi AI Security Analyst. Vysvětluj česky, jednoduše a krátce jako report pro školní projekt."
                    },
                    {
                        "role": "user",
                        "content": f"Shrň tento security report maximálně v 8 větách. Napiš, co je podezřelé a co zkontrolovat:\n{report}"
                    }
                ],
                max_completion_tokens=1200,
                reasoning_effort="low",
            )

            ai_summary = completion.choices[0].message.content

            if ai_summary:
                st.subheader("AI security summary")
                st.write(ai_summary)
            else:
                st.error("AI vrátila prázdnou odpověď.")
                st.write(completion)

    except Exception as e:
        st.error("AI summary se nepovedlo vygenerovat.")
        st.code(str(e))

st.subheader("Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Failed login IP", len(suspicious_failed_logins))
col2.metric("IP s hodně requesty", len(suspicious_many_requests))
col3.metric("Podezřelé URL", len(suspicious_urls))
col4.metric("Port scan IP", len(suspicious_port_scans))

st.bar_chart(requests_by_ip)