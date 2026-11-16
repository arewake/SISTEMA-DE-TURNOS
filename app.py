# app.py
import os
import json
import gradio as gr
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Importar nuestras herramientas reales conectadas a Firebase
from database.firebase_db import obtener_cliente_firestore, inicializar_datos_clinica_firebase
from database.crud_tools import (
    bloquear_turno_temporal,
    confirmar_turno,
    consultar_disponibilidad_especialista,
    aplicar_demora_en_cascada,
    guardar_mensaje_historial
)

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MANUAL_PATH = os.path.join("database", "manual_clinica.json")

# Inicializar datos base en Firebase al arrancar
try:
    inicializar_datos_clinica_firebase()
except Exception as e:
    print(f"⚠️ Aviso de inicialización Firebase: {e}")

# --- HERRAMIENTAS PARA GEMINI ---
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

herramientas_clinica = [
    consultar_manual_clinica,
    ver_disponibilidad,
    reservar_espacio_temporal,
    confirmar_turno_final
]

# --- LÓGICA DEL CHAT CON PERSISTENCIA EN FIREBASE ---
def responder_chat(mensaje, historial):
    telefono_prueba = "+5491122334455"
    try:
        # Guardar mensaje del paciente en Firebase
        guardar_mensaje_historial(telefono_prueba, "user", mensaje)
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        instrucciones = (
            "Eres el asistente inteligente de una clínica médica moderna. "
            "Especialistas disponibles: ESP_01 (Dr. Carlos Pérez - Cardiología), ESP_02 (Dra. Ana Gómez - Psiquiatría). "
            "El paciente actual es PAC_101 y la fecha de referencia es 2026-11-02. "
            "Si preguntan por estudios, obras sociales o reglas, usa 'consultar_manual_clinica'. "
            "Si piden turno, revisa disponibilidad con 'ver_disponibilidad' y bloquéalo con 'reservar_espacio_temporal'. "
            "Si detectas síntomas graves (dolor en el pecho), indica acudir a guardia de urgencia. "
            "Sé amable, claro y conciso."
        )
        
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=mensaje,
            config=types.GenerateContentConfig(
                system_instruction=instrucciones,
                tools=herramientas_clinica,
                temperature=0.3
            )
        )
        
        respuesta_texto = response.text
        # Guardar respuesta de la IA en Firebase
        guardar_mensaje_historial(telefono_prueba, "model", respuesta_texto)
        return respuesta_texto
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

# --- FUNCIONES PARA LEER FIREBASE EN VIVO ---
def obtener_estado_firebase():
    try:
        db = obtener_cliente_firestore()
        turnos = {doc.id: doc.to_dict() for doc in db.collection("turnos").stream()}
        especialistas = {doc.id: doc.to_dict() for doc in db.collection("especialistas").stream()}
        
        # Limpiar objetos timestamp para mostrar en JSON
        for t in turnos.values():
            if "creado_en" in t:
                t["creado_en"] = str(t["creado_en"])
                
        return (
            json.dumps(turnos, indent=2, ensure_ascii=False),
            json.dumps(especialistas, indent=2, ensure_ascii=False)
        )
    except Exception as e:
        return f"Error leyendo Firebase: {str(e)}", "{}"

def simular_demora(minutos):
    afectados = aplicar_demora_en_cascada("ESP_01", "2026-11-02", int(minutos))
    if afectados:
        return f"✅ Demora de {minutos} min aplicada en Firebase. Pacientes afectados:\n" + json.dumps(afectados, indent=2, ensure_ascii=False)
    return "ℹ️ No hay turnos confirmados hoy en Firebase para este especialista."

# --- DISEÑO DE INTERFAZ WEB CON GRADIO ---
with gr.Blocks(title="Clínica IA - Firebase Live", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏥 Clínica Inteligente - Prueba Integral con Firebase")
    gr.Markdown("Conectado en tiempo real a **Cloud Firestore** y **Gemini 3.5 Flash-Lite**.")
    
    with gr.Row():
        with gr.Column(scale=3):
            gr.ChatInterface(
                fn=responder_chat,
                chatbot=gr.Chatbot(height=450, placeholder="¡Hola! Ya estoy conectado a Firebase. ¿Qué turno o estudio necesitás consultar?"),
                textbox=gr.Textbox(placeholder="Ej: Hola, quiero un turno con el cardiólogo para el 2 de noviembre...")
            )
            
        with gr.Column(scale=2):
            gr.Markdown("### 🚨 Simulador de Demoras (Cascada en Firebase)")
            slider_minutos = gr.Slider(10, 60, value=20, step=10, label="Minutos de retraso (Dr. Pérez - ESP_01)")
            btn_demora = gr.Button("Disparar Alerta en Cascada", variant="primary")
            out_demora = gr.Textbox(label="Resultado de la Alerta", lines=4)
            btn_demora.click(fn=simular_demora, inputs=slider_minutos, outputs=out_demora)
            
            gr.Markdown("### ☁️ Datos en Vivo desde Firebase Firestore")
            btn_refresh = gr.Button("🔄 Consultar Nube de Firebase")
            out_turnos = gr.Code(label="Colección: turnos", language="json")
            out_esp = gr.Code(label="Colección: especialistas", language="json")
            
            btn_refresh.click(fn=obtener_estado_firebase, outputs=[out_turnos, out_esp])
            demo.load(fn=obtener_estado_firebase, outputs=[out_turnos, out_esp])

if __name__ == "__main__":
    demo.launch(inbrowser=True, share=True)
