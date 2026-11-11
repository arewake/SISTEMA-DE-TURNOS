# agents/agenda.py
from crewai import Agent
from crewai.tools import tool
from config.settings import obtener_llm
from database.crud_tools import bloquear_turno_temporal, confirmar_turno

# --- HERRAMIENTAS (TOOLS) DE ESCRITURA Y CONFIRMACIÓN ---

@tool("Reservar Espacio Temporalmente")
def tool_bloquear_turno(paciente_id: str, especialista_id: str, fecha: str, hora: str, duracion_minutos: int = 20) -> str:
    """
    Bloquea un turno en la base de datos de manera temporal por 5 minutos.
    Debe usarse cuando el paciente muestra interés en un horario pero aún no lo ha confirmado.
    Formatos requeridos: fecha (YYYY-MM-DD), hora (HH:MM).
    """
    try:
        resultado = bloquear_turno_temporal(paciente_id, especialista_id, fecha, hora, duracion_minutos)
        if resultado["exito"]:
            return f"ÉXITO: Espacio pre-reservado. ID de Operación: {resultado['turno_id']}. Mensaje: {resultado['mensaje']}"
        else:
            return f"FALLO: No se pudo reservar. Razón: {resultado['mensaje']}"
    except Exception as e:
        return f"Error en la operación de bloqueo: {str(e)}"

@tool("Confirmar Turno Pre-reservado")
def tool_confirmar_turno(turno_id: str) -> str:
    """
    Confirma definitivamente un turno que previamente fue bloqueado de forma temporal.
    Debe usarse inmediatamente después de que el paciente da el visto bueno final.
    """
    try:
        resultado = confirmar_turno(turno_id)
        if resultado["exito"]:
            return "ÉXITO: El turno ahora está confirmado de forma definitiva en el sistema."
        else:
            return f"FALLO: {resultado['mensaje']}"
    except Exception as e:
        return f"Error en la operación de confirmación: {str(e)}"


# --- DEFINICIÓN DEL AGENTE AGENDA ---
def crear_agente_agenda():
    """
    Inicializa el Agente de Agenda. 
    Usamos temperatura 0.1 (mínima) para garantizar precisión matemática y evitar errores.
    """
    llm_preciso = obtener_llm(temperature=0.1)
    
    return Agent(
        role="Administrador de Agenda Médica y Restricciones",
        goal="Garantizar la integridad de la agenda médica, evitando solapamientos y procesando reservas estrictas.",
        backstory=(
            "Eres un algoritmo de optimización con personalidad. Tu trabajo es puramente operativo. "
            "Recibes las solicitudes de los agentes orientados al cliente y te aseguras de impactar "
            "correctamente la base de datos. Eres el único autorizado para ejecutar bloqueos temporales "
            "y confirmaciones. Si detectas que un turno ya está tomado o bloqueado por otro proceso, "
            "rechazas la operación inmediatamente para proteger la experiencia del paciente y el médico."
        ),
        tools=[tool_bloquear_turno, tool_confirmar_turno],
        llm=llm_preciso,
        verbose=True
    )
