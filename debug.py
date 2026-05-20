import os
from dotenv import load_dotenv

# Načti .env
load_dotenv()

# Vypiš výsledek
klic = os.getenv("AZURE_OPENAI_API_KEY")
if klic:
    print(f"Klíč je načten, začíná znaky: {klic[:5]}...")
else:
    print("CHYBA: Klíč se nenačetl.")