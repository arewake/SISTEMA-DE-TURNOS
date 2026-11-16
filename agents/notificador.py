# agents/notificador.py
from crewai import Agent
from crewai.tools import tool
from config.settings import obtener_llm
from database.simulacion_db import cargar_db, guardar_db
from database.crud_tools import aplicar_demora_en_cascada

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
        
        paciente_asignado = lista.pop(0) 
        guardar_db(db)
        
        return (
            f"ÉXITO: Se detectó al paciente {paciente_asignado['paciente_id']} en lista de espera. "
            f"Se ha generado una propuesta de reubicación automática para las {hora_libre}."
        )
    except Exception as e:
        return f"Error al procesar lista de espera: {str(e)}"

@tool("Gestionar Demora en Cascada de Especialista")
def tool_gestionar_demora_cascada(especialista_id: str, fecha: str, minutos_retraso: int) -> str:
    """
    Aplica un retraso en minutos a toda la agenda confirmada de un especialista en una fecha.
    Devuelve la lista exacta de pacientes afectados con sus nuevos horarios estimados para avisarles.
    """
    try:
        afectados = aplicar_demora_en_cascada(especialista_id, fecha, minutos_retraso)
        if not afectados:
            return f"No hay turnos confirmados afectados para {especialista_id} en la fecha {fecha}."
        
        reporte = f"ALERTA DE CASCADA: Se aplicó un retraso de {minutos_retraso} min. Pacientes afectados:\n"
        for p in afectados:
            reporte += (
                f"- {p['paciente_nombre']} (Tel: {p['telefono']}): "
                f"Turno original {p['hora_original']} -> Nuevo horario estimado {p['nueva_hora_estimada']}.\n"
            )
        return reporte
    except Exception as e:
        return f"Error al calcular demora en cascada: {str(e)}"

def crear_agente_seguimiento():
    """Inicializa el Agente Notificador y Optimizador con capacidades de cancelación y demoras."""
    llm_resolutivo = obtener_llm(temperature=0.3)
    
    return Agent(
        role="Especialista en Seguimiento, Demoras y Optimización de Agenda",
        goal="Reducir el ausentismo, optimizar huecos por cancelaciones y gestionar proactivamente las demoras de los médicos.",
        backstory=(
            "Eres el estratega logístico de la clínica. Sabes que el tiempo de los pacientes es oro. "
            "Cuando un turno se cancela, reubicas rápido a alguien de la lista de espera. "
            "Cuando un médico se retrasa, calculas el impacto en cascada y redactas mensajes claros y empáticos "
            "para que los pacientes siguientes no pierdan tiempo en la sala de espera."
        ),
        tools=[tool_cancelar_y_liberar, tool_asignar_lista_espera, tool_gestionar_demora_cascada],
        llm=llm_resolutivo,
        verbose=True
    )
