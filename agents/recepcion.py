# agents/recepcion.py
from crewai import Agent
from crewai.tools import tool
from config.settings import obtener_llm
from database.crud_tools import consultar_disponibilidad_especialista

# --- COUPLING DE HERRAMIENTAS (TOOLS) PARA EL AGENTE ---
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
        msg += "Analiza los espacios libres basándote en la duración base del médico."
        return msg
    except Exception as e:
        return f"Error al consultar la disponibilidad: {str(e)}"


# --- DEFINICIÓN DEL AGENTE MODERNO ---
def crear_agente_recepcion():
    """
    Inicializa el Agente de Recepción configurado con Gemini 2.0 Flash
    y sus herramientas de acceso al sistema de turnos.
    """
    # Usamos una temperatura ligeramente más alta (0.6) para que sea empático y natural al hablar
    llm_gemini = obtener_llm(temperature=0.6)
    
    return Agent(
        role="Recepcionista Médico Virtual Inteligente",
        goal="Interactuar de forma empática, eficiente y resolutiva con los pacientes para gestionar sus solicitudes de turnos.",
        backstory=(
            "Eres el pilar de atención al cliente de una clínica médica de vanguardia. "
            "Tu trato es sumamente profesional, humano y comprensivo. Entiendes que las personas "
            "que te contactan pueden estar lidiando con problemas de salud, por lo que eres paciente. "
            "Tu objetivo es resolver sus dudas de horarios utilizando tus herramientas y derivar "
            "la información de manera limpia al sistema de agenda. Nunca inventas horarios; siempre consultas "
            "tu herramienta de disponibilidad antes de confirmar opciones al paciente."
        ),
        tools=[tool_consultar_disponibilidad],
        llm=llm_gemini,
        verbose=True,  # Permite ver en la consola el "pensamiento" del agente en tiempo real
        memory=True    # Permite al agente recordar el contexto de la conversación actual
    )
