# agents/recepcion.py
from crewai import Agent
from crewai.tools import tool
from config.settings import obtener_llm
from database.crud_tools import consultar_disponibilidad_especialista
from database.rag_tools import tool_consultar_rag_clinica

@tool("Consultar Disponibilidad de Especialista")
def tool_consultar_disponibilidad(especialista_id: str, fecha: str) -> str:
    """
    Busca los bloques de trabajo y turnos ocupados para un especialista en una fecha específica.
    El formato de fecha debe ser YYYY-MM-DD (ejemplo: 2026-11-02).
    """
    try:
        resultado = consultar_disponibilidad_especialista(especialista_id, fecha)
        if not resultado["bloques_laborales"]:
            return f"El especialista {especialista_id} no atiende en la fecha {fecha}."
        
        msg = f"Disponibilidad para {especialista_id} el {fecha}:\n"
        msg += f"- Bloque de atención: {resultado['bloques_laborales'][0]['hora_inicio']} a {resultado['bloques_laborales'][0]['hora_fin']}\n"
        msg += f"- Turnos actualmente ocupados u ocupados temporalmente: {resultado['turnos_ocupados']}\n"
        return msg
    except Exception as e:
        return f"Error al consultar la disponibilidad: {str(e)}"

def crear_agente_recepcion():
    llm_gemini = obtener_llm(temperature=0.4)
    
    return Agent(
        role="Recepcionista Médico Virtual Inteligente",
        goal="Atender consultas administrativas, informar preparaciones de estudios y gestionar turnos con precisión.",
        backstory=(
            "Eres el pilar de atención al cliente de una clínica médica moderna. "
            "Tienes acceso directo a la disponibilidad de los médicos y al Manual Oficial de la Clínica. "
            "Cuando un paciente pregunta sobre obras sociales, preparaciones para estudios (como Holter o ECG) "
            "o políticas de cancelación, SIEMPRE usas tu herramienta de consulta del manual antes de responder. "
            "Nunca inventas requisitos médicos ni administrativos."
        ),
        # Aquí le damos ambas herramientas: Agenda + RAG
        tools=[tool_consultar_disponibilidad, tool_consultar_rag_clinica],
        llm=llm_gemini,
        verbose=True
    )
