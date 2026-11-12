# database/crud_tools.py
from datetime import datetime, timedelta
from firebase_admin import firestore
from .firebase_db import obtener_cliente_firestore

# --- 1. GESTIÓN DE TURNOS Y BLOQUEOS ---

def bloquear_turno_temporal(paciente_id: str, especialista_id: str, fecha: str, hora: str, duracion_minutos: int = 20):
    """Bloquea un turno en Firestore por 5 minutos para evitar reservas dobles."""
    db = obtener_cliente_firestore()
    turnos_ref = db.collection("turnos")
    
    # Consultar si ya existe un turno para ese médico, fecha y hora
    query = (
        turnos_ref
        .where("especialista_id", "==", especialista_id)
        .where("fecha", "==", fecha)
        .where("hora_estimada", "==", hora)
        .stream()
    )
    
    ahora = datetime.now()
    for doc in query:
        t = doc.to_dict()
        if t["estado"] == "confirmado":
            return {"exito": False, "mensaje": "El horario ya está confirmado por otro paciente."}
        if t["estado"] == "reserva_temporal" and t.get("bloqueado_hasta"):
            expiracion = datetime.strptime(t["bloqueado_hasta"], "%Y-%m-%d %H:%M:%S")
            if expiracion > ahora:
                return {"exito": False, "mensaje": "El horario está reservado temporalmente en este instante."}

    turno_id = f"TURNO_{int(ahora.timestamp())}"
    expiracion_bloqueo = (ahora + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

    nuevo_turno = {
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
        },
        "creado_en": firestore.SERVER_TIMESTAMP
    }
    
    turnos_ref.document(turno_id).set(nuevo_turno)
    return {"exito": True, "turno_id": turno_id, "mensaje": f"Espacio bloqueado hasta {expiracion_bloqueo}."}

def confirmar_turno(turno_id: str):
    """Confirma definitivamente un turno en Firestore."""
    db = obtener_cliente_firestore()
    doc_ref = db.collection("turnos").document(turno_id)
    if doc_ref.get().exists:
        doc_ref.update({
            "estado": "confirmado",
            "bloqueado_hasta": None
        })
        return {"exito": True, "mensaje": "Turno confirmado exitosamente en la nube."}
    return {"exito": False, "mensaje": "El ID de turno no existe."}

def cancelar_turno_y_liberar(turno_id: str):
    """Cancela un turno en Firestore y devuelve los datos del hueco liberado."""
    db = obtener_cliente_firestore()
    doc_ref = db.collection("turnos").document(turno_id)
    doc = doc_ref.get()
    
    if doc.exists:
        datos = doc.to_dict()
        doc_ref.update({"estado": "cancelado"})
        return {
            "exito": True,
            "especialista_id": datos["especialista_id"],
            "fecha": datos["fecha"],
            "hora": datos["hora_estimada"]
        }
    return {"exito": False, "mensaje": "Turno no encontrado."}

def consultar_disponibilidad_especialista(especialista_id: str, fecha: str):
    """Consulta bloques de trabajo y turnos ocupados en Firestore."""
    db = obtener_cliente_firestore()
    
    bloques_docs = (
        db.collection("bloques_disponibilidad")
        .where("especialista_id", "==", especialista_id)
        .where("fecha", "==", fecha)
        .where("estado", "==", "activo")
        .stream()
    )
    bloques = [doc.to_dict() for doc in bloques_docs]
    
    turnos_docs = (
        db.collection("turnos")
        .where("especialista_id", "==", especialista_id)
        .where("fecha", "==", fecha)
        .stream()
    )
    
    turnos_activos = []
    for doc in turnos_docs:
        t = doc.to_dict()
        if t["estado"] in ["confirmado", "reserva_temporal"]:
            turnos_activos.append({
                "hora": t["hora_estimada"],
                "duracion": t["duracion_asignada_minutos"],
                "estado": t["estado"]
            })
            
    return {"bloques_laborales": bloques, "turnos_ocupados": turnos_activos}

# --- 2. DEMORAS EN CASCADA Y LISTA DE ESPERA ---

def aplicar_demora_en_cascada(especialista_id: str, fecha: str, minutos_retraso: int):
    """Actualiza el retraso acumulado en Firestore y retorna los pacientes afectados."""
    db = obtener_cliente_firestore()
    turnos_docs = (
        db.collection("turnos")
        .where("especialista_id", "==", especialista_id)
        .where("fecha", "==", fecha)
        .where("estado", "==", "confirmado")
        .stream()
    )
    
    pacientes_afectados = []
    for doc in turnos_docs:
        turno = doc.to_dict()
        retraso_previo = turno.get("metricas", {}).get("retraso_detectado_minutos", 0)
        nuevo_retraso = retraso_previo + minutos_retraso
        
        # Actualizar documento en Firebase
        doc.reference.update({"metricas.retraso_detectado_minutos": nuevo_retraso})
        
        hora_original = datetime.strptime(turno["hora_estimada"], "%H:%M")
        nueva_hora = (hora_original + timedelta(minutes=nuevo_retraso)).strftime("%H:%M")
        
        # Buscar datos del paciente
        pac_doc = db.collection("pacientes").document(turno["paciente_id"]).get()
        datos_pac = pac_doc.to_dict() if pac_doc.exists else {"nombre": "Paciente", "telefono": "Desconocido"}
        
        pacientes_afectados.append({
            "turno_id": doc.id,
            "paciente_nombre": datos_pac.get("nombre"),
            "telefono": datos_pac.get("telefono"),
            "hora_original": turno["hora_estimada"],
            "nueva_hora_estimada": nueva_hora,
            "retraso_total_minutos": nuevo_retraso
        })
        
    return pacientes_afectados

# --- 3. MEMORIA CONVERSACIONAL PERSISTENTE ---

def guardar_mensaje_historial(telefono_paciente: str, rol: str, contenido: str):
    """Guarda cada mensaje del chat (WhatsApp/Web) en Firebase para mantener contexto histórico."""
    db = obtener_cliente_firestore()
    db.collection("historial_chats").document(telefono_paciente).collection("mensajes").add({
        "rol": rol, # 'user' o 'model'
        "contenido": contenido,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def obtener_historial_paciente(telefono_paciente: str, limite: int = 10):
    """Recupera los últimos mensajes de un paciente para que la IA tenga memoria."""
    db = obtener_cliente_firestore()
    docs = (
        db.collection("historial_chats")
        .document(telefono_paciente)
        .collection("mensajes")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limite)
        .stream()
    )
    mensajes = [doc.to_dict() for doc in docs]
    mensajes.reverse() # Orden cronológico
    return mensajes
