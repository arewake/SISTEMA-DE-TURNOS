# servidor_clinica.py
import os
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from database.firebase_db import obtener_cliente_firestore, inicializar_datos_clinica_firebase
from database.crud_tools import aplicar_demora_en_cascada
from agents.orquestador_ia import procesar_mensaje_paciente

load_dotenv()

app = FastAPI(title="API Clínica Inteligente")

# Permitir conexiones desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables para conectar con WhatsApp Cloud API (Meta) cuando salgas a producción
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "clinica_secreto_2026")

# Inicializar datos base en Firebase al arrancar
@app.on_event("startup")
def startup_event():
    try:
        inicializar_datos_clinica_firebase()
    except Exception as e:
        print(f"⚠️ Aviso Firebase: {e}")

# --- 1. SERVIR EL PANEL VISUAL DE SECRETARIAS ---
@app.get("/", response_class=HTMLResponse)
def abrir_panel_web():
    ruta_html = os.path.join(os.path.dirname(__file__), "panel_secretaria.html")
    with open(ruta_html, "r", encoding="utf-8") as f:
        return f.read()

# --- 2. ENDPOINTS PARA EL PANEL ADMINISTRATIVO ---
@app.get("/api/datos")
def obtener_datos_panel():
    """Devuelve todos los turnos y especialistas desde Firebase para el panel visual."""
    db = obtener_cliente_firestore()
    turnos = []
    for doc in db.collection("turnos").stream():
        t = doc.to_dict()
        t["id"] = doc.id
        if "creado_en" in t:
            t["creado_en"] = str(t["creado_en"])
        turnos.append(t)
        
    especialistas = {doc.id: doc.to_dict() for doc in db.collection("especialistas").stream()}
    return {"turnos": turnos, "especialistas": especialistas}

class SolicitudDemora(BaseModel):
    especialista_id: str
    fecha: str
    minutos: int

@app.post("/api/demora")
def disparar_demora_cascada(datos: SolicitudDemora):
    """Aplica retraso en Firebase y envía WhatsApp automático a los afectados."""
    afectados = aplicar_demora_en_cascada(datos.especialista_id, datos.fecha, datos.minutos)
    
    # Enviar notificación real por WhatsApp si está configurado el token
    for pac in afectados:
        mensaje_aviso = (
            f"Hola {pac['paciente_nombre']}, te avisamos de la clínica que el especialista "
            f"presenta una demora de {datos.minutos} min. Tu nuevo horario estimado de atención es a las {pac['nueva_hora_estimada']} hs."
        )
        enviar_whatsapp_saliente(pac["telefono"], mensaje_aviso)
        
    return {"mensaje": f"Demora aplicada a {len(afectados)} pacientes.", "afectados": afectados}

@app.post("/api/checkin/{turno_id}")
def marcar_llegada_paciente(turno_id: str):
    """Marca que el paciente ya llegó a la sala de espera."""
    db = obtener_cliente_firestore()
    db.collection("turnos").document(turno_id).update({"estado": "en_espera_sala"})
    return {"mensaje": "Paciente marcado en sala de espera."}

class MensajeSimulado(BaseModel):
    telefono: str
    texto: str

@app.post("/api/chat_prueba")
def chat_desde_panel(msg: MensajeSimulado):
    """Permite probar el bot de WhatsApp directamente desde el panel web."""
    respuesta = procesar_mensaje_paciente(msg.telefono, msg.texto)
    return {"respuesta": respuesta}

# --- 3. WEBHOOK OFICIAL DE WHATSAPP (META CLOUD API) ---
@app.get("/webhook")
def verificar_webhook_whatsapp(request: Request):
    """Validación requerida por Meta para conectar el número de WhatsApp."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Token de verificación inválido")

@app.post("/webhook")
async def recibir_mensaje_whatsapp(request: Request):
    """Recibe los mensajes que los pacientes envían al WhatsApp de la clínica."""
    body = await request.json()
    try:
        entry = body["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            mensaje_obj = entry["messages"][0]
            telefono_paciente = mensaje_obj["from"]
            texto_paciente = mensaje_obj["text"]["body"]
            
            # Procesar con Gemini + Firebase
            respuesta_ia = procesar_mensaje_paciente(telefono_paciente, texto_paciente)
            
            # Responder al WhatsApp del paciente
            enviar_whatsapp_saliente(telefono_paciente, respuesta_ia)
    except Exception as e:
        print(f"Error procesando webhook: {e}")
    return {"status": "ok"}

def enviar_whatsapp_saliente(telefono: str, texto: str):
    """Envía un mensaje de WhatsApp usando la API oficial de Meta."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        print(f"📲 [SIMULACIÓN WHATSAPP -> {telefono}]: {texto}")
        return
    url = f"https://facebook.com{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }
    requests.post(url, json=payload, headers=headers)
