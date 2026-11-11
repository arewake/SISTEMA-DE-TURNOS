# database/crud_tools.py
from datetime import datetime, timedelta
from .simulacion_db import cargar_db, guardar_db

def bloquear_turno_temporal(paciente_id, especialista_id, fecha, hora, duracion_minutos=20):
    """
    Bloquea un espacio de tiempo por 5 minutos para que ningún otro agente lo tome
    mientras el paciente confirma la cita.
    """
    db = cargar_db()
    
    # Generar un ID único para el turno simulado
    turno_id = f"TURNO_{int(datetime.now().timestamp())}"
    
    # Calcular el tiempo de expiración del bloqueo (5 minutos desde ahora)
    expiracion_bloqueo = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Verificar si hay solapamiento (Double-booking protection)
    for t in db["turnos"].values():
        if t["especialista_id"] == especialista_id and t["fecha"] == fecha and t["hora_estimada"] == hora:
            if t["estado"] == "confirmado" or (t["estado"] == "reserva_temporal" and datetime.strptime(t["bloqueado_hasta"], "%Y-%m-%d %H:%M:%S") > datetime.now()):
                return {"exito": False, "mensaje": "El espacio ya está ocupado o reservado temporalmente."}

    # Crear el registro con estado temporal
    db["turnos"][turno_id] = {
        "paciente_id": paciente_id,
        "especialista_id": especialista_id,
        "fecha": fecha,
        "hora_estimada": hora,
        "duracion_asignada_minutos": duracion_minutos,
        "estado": "reserva_temporal",
        "bloqueado_hasta": expiracion_bloqueo,
        "metricas": {
            "hora_llegada_real": None,
            "hora_inicio_real": None,
            "retraso_detectado_minutos": 0
        }
    }
    
    guardar_db(db)
    return {"exito": True, "turno_id": turno_id, "mensaje": f"Espacio bloqueado temporalmente hasta {expiracion_bloqueo}."}

def confirmar_turno(turno_id):
    """Pasa el estado del turno de 'reserva_temporal' a 'confirmado'."""
    db = cargar_db()
    if turno_id in db["turnos"]:
        db["turnos"][turno_id]["estado"] = "confirmado"
        db["turnos"][turno_id]["bloqueado_hasta"] = None
        guardar_db(db)
        return {"exito": True, "mensaje": "Turno confirmado exitosamente."}
    return {"exito": False, "mensaje": "El ID de turno no existe."}

def consultar_disponibilidad_especialista(especialista_id, fecha):
    """Retorna los turnos ocupados y los bloques de trabajo de un especialista."""
    db = cargar_db()
    bloques = [b for b in db["bloques_disponibilidad"].values() if b["especialista_id"] == especialista_id and b["fecha"] == fecha]
    turnos_activos = [
        {"hora": t["hora_estimada"], "duracion": t["duracion_asignada_minutos"], "estado": t["estado"]}
        for t in db["turnos"].values()
        if t["especialista_id"] == especialista_id and t["fecha"] == fecha and t["estado"] in ["confirmado", "reserva_temporal"]
    ]
    
    return {
        "bloques_laborales": bloques,
        "turnos_ocupados": turnos_activos
    }
