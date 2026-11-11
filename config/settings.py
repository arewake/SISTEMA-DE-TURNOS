# config/settings.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Validar que la API Key esté presente obligatoriamente
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "❌ ERROR: No se encontró la variable GEMINI_API_KEY en el archivo .env.\n"
        "Por favor, crea un archivo .env en la raíz del proyecto y agrega tu clave."
    )

def obtener_llm(temperature=0.5):
    """
    Retorna una instancia configurada de Gemini 2.0 Flash.
    Utilizamos una temperatura moderada por defecto para balancear la creatividad 
    del agente recepcionista con la precisión del agente de agenda.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=temperature
    )
