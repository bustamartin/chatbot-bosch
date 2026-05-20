from openai import OpenAI
import os

def vygeneruj_web(firma, obor, styl, client, deployment_name):
    prompt = f"""
    Jsi expert na tvorbu webů. Vytvoř obsah pro firmu '{firma}', která se zabývá '{obor}'.
    Styl webu musí být: '{styl}'.
    
    Vrať mi výsledek ve formátu:
    Slogan: [slogan]
    Sekce: [seznam sekcí]
    Barvy: [HEX kódy barev]
    HTML_Kod: [kompletní kód jedné HTML stránky s inline CSS]
    """
    
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content