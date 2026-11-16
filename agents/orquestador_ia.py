# agents/orquestador_ia.py
import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

from database.crud_tools import (
    bloquear_turno_temporal,
    confirmar_turno,
    cancelar_turno_y_liberar,
    consultar_disponibilidad_especialista,
    guardar_mensaje_historial,
    obtener_historial_paciente
)

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MANUAL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "manual_clinica.json")

# --- HERRAMIENTAS DE ACCIÓN PARA EL MODELO ---
def consultar_manual_clinica(consulta: str) -> str:
    """Consulta el manual oficial sobre preparación de estudios, obras sociales y políticas."""
    if not os.path.exists(MANUAL_PATH):
        return "Manual no disponible."
    with open(MANUAL_PATH, "r", encoding="utf-8") as f:
        manual = json.load(f)
    return json.dumps(manual, ensure_ascii=False)

def ver_disponibilidad(especialista_id: str, fecha: str) -> str:
    """Consulta bloques laborales y turnos ocupados en Firebase. Formato fecha: YYYY-MM-DD."""
    res = consultar_disponibilidad_especialista(especialista_id, fecha)
    return json.dumps(res, ensure_ascii=False)

def reservar_espacio_temporal(paciente_id: str, especialista_id: str, fecha: str, hora: str) -> str:
    """Bloquea un turno en Firebase por 5 minutos. Formato fecha: YYYY-MM-DD, hora: HH:MM."""
    res = bloquear_turno_temporal(paciente_id, especialista_id, fecha, hora)
    return json.dumps(res, ensure_ascii=False)

def confirmar_turno_final(turno_id: str) -> str:
    """Confirma de forma definitiva un turno previamente bloqueado en Firebase."""
    res = confirmar_turno(turno_id)
    return json.dumps(res, ensure_ascii=False)

def cancelar_turno_paciente(turno_id: str) -> str:
    """Cancela un turno existente y libera el espacio en Firebase."""
    res = cancelar_turno_y_liberar(turno_id)
    return json.dumps(res, ensure_ascii=False)

HERRAMIENTAS = [
    consultar_manual_clinica,
    ver_disponibilidad,
    reservar_espacio_temporal,
    confirmar_turno_final,
    cancelar_turno_paciente
]

# --- FUNCIÓN PRINCIPAL DE PROCESAMIENTO ---
def procesar_mensaje_paciente(telefono: str, mensaje_texto: str) -> str:
    """
    Recibe el teléfono y mensaje del paciente, recupera su memoria de Firebase,
    procesa la intención con Gemini y guarda la nueva interacción.
    """
    try:
        # 1. Guardar mensaje entrante en Firebase
        guardar_mensaje_historial(telefono, "user", mensaje_texto)
        
        # 2. Recuperar los últimos 6 mensajes para tener contexto de la charla
        historial_previo = obtener_historial_paciente(telefono, limite=6)
        contexto_chat = "\n".join([f"{m['rol'].upper()}: {m['contenido']}" for m in historial_previo])

        client = genai.Client(api_key=GEMINI_API_KEY)
        
        instrucciones = (
            "Eres el asistente virtual oficial de una clínica médica moderna. "
            "Especialistas disponibles: ESP_01 (Dr. Carlos Pérez - Cardiología), ESP_02 (Dra. Ana Gómez - Psiquiatría). "
            f"El identificador del paciente actual es '{telefono}'. "
            "Reglas de operación:\n"
            "1. Si preguntan por preparación de estudios, obras sociales o políticas, usa 'consultar_manual_clinica'.\n"
            "2. Si piden turno, consulta disponibilidad con 'ver_disponibilidad' y bloquéalo con 'reservar_espacio_temporal'. "
            "Indícale el ID de reserva y dile que responda 'Confirmo' en los próximos 5 minutos.\n"
            "3. Si dice 'Confirmo' o acepta el turno bloqueado, usa 'confirmar_turno_final' con el ID de la conversación.\n"
            "4. Si pide cancelar, usa 'cancelar_turno_paciente'.\n"
            "5. Si describe síntomas graves (dolor en el pecho, falta de aire severa), indícale acudir de inmediato a la guardia.\n"
            "Sé amable, empático y conciso (ideal para leer desde WhatsApp)."
        )

        prompt_completo = f"Historial reciente de la conversación:\n{contexto_chat}\n\nNuevo mensaje del paciente: {mensaje_texto}"

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt_completo,
            config=types.GenerateContentConfig(
                system_instruction=instrucciones,
                tools=HERRAMIENTAS,
                temperature=0.3
            )
        )
        
        respuesta_final = response.text
        
        # 3. Guardar respuesta de la IA en Firebase
        guardar_mensaje_historial(telefono, "model", respuesta_final)
        return respuesta_final
        
    except Exception as e:
        return f"Disculpa, estamos teniendo una demora técnica en el sistema. Por favor intenta en unos minutos. (Detalle: {str(e)})"
