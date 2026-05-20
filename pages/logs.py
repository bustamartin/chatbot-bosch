import streamlit as st
import pandas as pd

df = pd.read_csv("logs/security_logs.csv")

failed_logins = df[df["event"] == "failed_login"]
failed_by_ip = failed_logins["ip"].value_counts()
suspicious_failed_logins = failed_by_ip[failed_by_ip >= 3]

requests_by_ip = df["ip"].value_counts()
suspicious_many_requests = requests_by_ip[requests_by_ip >= 5]

dangerous_urls = ["/admin", "/wp-admin", "/phpmyadmin", "/.env", "/etc/passwd", "/config.php", "/backup.zip", "/db.sql"]
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