# agents/notificador.py
from crewai import Agent
from crewai.tools import tool
from config.settings import obtener_llm
from database.simulacion_db import cargar_db, guardar_db

# --- HERRAMIENTAS (TOOLS) PARA OPTIMIZAR CANCELACIONES ---

@tool("Procesar Cancelación y Liberar Espacio")
def tool_cancelar_y_liberar(turno_id: str) -> str:
    """
    Cancela un turno existente modificando su estado a 'cancelado'.
    Esto libera inmediatamente el bloque horario en la base de datos de la clínica.
    """
    try:
        db = cargar_db()
        if turno_id in db["turnos"]:
            db["turnos"][turno_id]["estado"] = "cancelado"
            especialista = db["turnos"][turno_id]["especialista_id"]
            fecha = db["turnos"][turno_id]["fecha"]
            hora = db["turnos"][turno_id]["hora_estimada"]
            
            guardar_db(db)
            return f"ÉXITO: Turno {turno_id} cancelado. Espacio liberado para {especialista} el {fecha} a las {hora}."
        return "FALLO: El ID de turno no existe."
    except Exception as e:
        return f"Error al cancelar turno: {str(e)}"

@tool("Consultar y Asignar Lista de Espera")
def tool_asignar_lista_espera(especialista_id: str, fecha: str, hora_libre: str) -> str:
    """
    Revisa si hay pacientes esperando un lugar para ese especialista y asigna el hueco libre.
    """
    try:
        db = cargar_db()
        lista = db.get("lista_espera_dinamica", [])
        
        if not lista:
            return "INFORMACIÓN: No hay pacientes en lista de espera para este día. El hueco queda libre."
        
        # Simular que tomamos al primer paciente elegible de la lista
        paciente_asignado = lista.pop(0) 
        guardar_db(db)
        
        return (
            f"ÉXITO: Se detectó al paciente {paciente_asignado['paciente_id']} en lista de espera. "
            f"Se ha generado una propuesta de reubicación automática para las {hora_libre}."
        )
    except Exception as e:
        return f"Error al procesar lista de espera: {str(e)}"


# --- DEFINICIÓN DEL AGENTE ---
def crear_agente_seguimiento():
    """Inicializa el Agente Notificador y Optimizador."""
    llm_resolutivo = obtener_llm(temperature=0.2)
    
    return Agent(
        role="Especialista en Seguimiento y Optimización de Agenda",
        goal="Reducir el ausentismo, procesar cancelaciones y rellenar huecos vacíos de forma proactiva utilizando listas de espera.",
        backstory=(
            "Eres el estratega logístico de la clínica. Odias ver un hueco vacío en la agenda de un médico "
            "porque sabes que significa tiempo perdido para el especialista y un paciente que se quedó sin atención. "
            "Cuando te notifican una cancelación, actúas de inmediato interactuando con las herramientas de la base de datos "
            "para mover a los pacientes de la lista de espera al nuevo espacio disponible."
        ),
        tools=[tool_cancelar_y_liberar, tool_asignar_lista_espera],
        llm=llm_resolutivo,
        verbose=True
    )
