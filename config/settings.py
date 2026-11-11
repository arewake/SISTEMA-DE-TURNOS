# config/settings.py
import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "❌ ERROR: No se encontró la variable GEMINI_API_KEY en el archivo .env.\n"
        "Por favor, crea un archivo .env en la raíz del proyecto y agrega tu clave."
    )

def obtener_llm(temperature=0.5):
    """
    Retorna una instancia nativa de LLM de CrewAI configurada con el modelo vigente Gemini 3.8 Flash.
    """
    return LLM(
        model="gemini/gemini-3.8-flash",
        api_key=GEMINI_API_KEY,
        temperature=temperature
    )
