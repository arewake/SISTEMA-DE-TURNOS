# app.py
import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Importar nuestras herramientas reales de datos y RAG
from database.simulacion_db import cargar_db
from database.crud_tools import (
    bloquear_turno_temporal,
    confirmar_turno,
    consultar_disponibilidad_especialista,
    aplicar_demora_en_cascada
)
MANUAL_PATH = os.path.join("database", "manual_clinica.json")

import json

# Cargar configuración y clave API
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="Clínica IA - Turnos", page_icon="🏥", layout="wide")
st.title("🏥 Clínica Inteligente - Gestión Autónoma de Turnos")
st.markdown("Sistema impulsado directamente por el SDK nativo de **Gemini 3.8 Flash**.")

# --- DEFINICIÓN DE FUNCIONES NATIVAS PARA GEMINI ---
def consultar_manual_clinica(consulta: str) -> str:
    """Consulta el manual oficial sobre preparación de estudios, obras sociales y políticas."""
    if not os.path.exists(MANUAL_PATH):
        return "Manual no disponible."
    with open(MANUAL_PATH, "r", encoding="utf-8") as f:
        manual = json.load(f)
    return json.dumps(manual, ensure_ascii=False)

def ver_disponibilidad(especialista_id: str, fecha: str) -> str:
    """Consulta bloques laborales y turnos ocupados. Formato fecha: YYYY-MM-DD."""
    res = consultar_disponibilidad_especialista(especialista_id, fecha)
    return json.dumps(res, ensure_ascii=False)

def reservar_espacio_temporal(paciente_id: str, especialista_id: str, fecha: str, hora: str) -> str:
    """Bloquea un turno por 5 minutos. Formato fecha: YYYY-MM-DD, hora: HH:MM."""
    res = bloquear_turno_temporal(paciente_id, especialista_id, fecha, hora)
    return json.dumps(res, ensure_ascii=False)

def confirmar_turno_final(turno_id: str) -> str:
    """Confirma de forma definitiva un turno previamente bloqueado."""
    res = confirmar_turno(turno_id)
    return json.dumps(res, ensure_ascii=False)

# Lista de herramientas que Gemini puede ejecutar solo
herramientas_clinica = [
    consultar_manual_clinica,
    ver_disponibilidad,
    reservar_espacio_temporal,
    confirmar_turno_final
]

# --- INICIALIZAR MEMORIA DEL CHAT ---
if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {"role": "assistant", "content": "¡Hola! Soy el asistente de la clínica. ¿En qué te puedo ayudar hoy?"}
    ]

# --- FUNCIÓN DE RESPUESTA DIRECTA SIN BLOQUEOS ---
def responder_con_gemini(prompt_usuario):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        instrucciones_sistema = (
            "Eres el asistente inteligente de una clínica médica moderna. "
            "Especialistas disponibles: ESP_01 (Dr. Carlos Pérez - Cardiología), ESP_02 (Dra. Ana Gómez - Psiquiatría). "
            "El paciente actual es PAC_101 y la fecha de referencia para pruebas es 2026-11-02. "
            "Si preguntan por estudios, obras sociales o reglas, usa 'consultar_manual_clinica'. "
            "Si piden turno, revisa disponibilidad con 'ver_disponibilidad' y bloquéalo con 'reservar_espacio_temporal'. "
            "Si detectas síntomas graves (dolor en el pecho), indica acudir a guardia de urgencia. "
            "Sé amable, claro y conciso."
        )

        # Llamada directa con ejecución automática de herramientas
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt_usuario,
            config=types.GenerateContentConfig(
                system_instruction=instrucciones_sistema,
                tools=herramientas_clinica,
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        return f"❌ Error al conectar con Gemini: {str(e)}"

# --- INTERFAZ EN DOS COLUMNAS ---
col_chat, col_panel = st.columns([1.2, 1])

with col_chat:
    st.subheader("💬 Canal de Atención al Paciente")
    contenedor_chat = st.container(height=450)
    with contenedor_chat:
        for msg in st.session_state.mensajes:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("Escribí tu consulta acá (ej: ¿Cómo me preparo para un Holter?)..."):
        st.session_state.mensajes.append({"role": "user", "content": prompt})
        with contenedor_chat:
            with st.chat_message("user"):
                st.markdown(prompt)

        with contenedor_chat:
            with st.chat_message("assistant"):
                with st.spinner("Consultando sistema..."):
                    respuesta = responder_con_gemini(prompt)
                    st.markdown(respuesta)
        
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
        st.rerun()

with col_panel:
    st.subheader("📊 Monitor de la Clínica (En Tiempo Real)")
    
    with st.expander("🚨 Simulador de Demoras Médicas (Cascada)", expanded=True):
        st.write("Simulá que el **Dr. Carlos Pérez (ESP_01)** se atrasó:")
        minutos = st.slider("Minutos de retraso", 10, 60, 20, step=10)
        if st.button("Disparar Alerta en Cascada", type="primary"):
            afectados = aplicar_demora_en_cascada("ESP_01", "2026-11-02", minutos)
            if afectados:
                st.success(f"¡Demora aplicada! Se notificó a {len(afectados)} paciente(s).")
                st.json(afectados)
            else:
                st.warning("No hay turnos confirmados hoy para este especialista.")

        # --- REEMPLAZAR DESDE AQUÍ HASTA EL FINAL DE app.py ---
    st.markdown("### 📊 Panel Operativo de la Clínica")
    if st.button("🔄 Actualizar Panel"):
        st.rerun()
        
    db_actual = cargar_db()
    turnos_dict = db_actual.get("turnos", {})
    lista_espera = db_actual.get("lista_espera_dinamica", [])
    especialistas_dict = db_actual.get("especialistas", {})
    pacientes_dict = db_actual.get("pacientes", {})

    # 1. Tarjetas de Métricas Rápidas (KPIs)
    m1, m2, m3 = st.columns(3)
    turnos_activos = sum(1 for t in turnos_dict.values() if t["estado"] in ["confirmado", "reserva_temporal"])
    m1.metric("Turnos Activos", turnos_activos)
    m2.metric("En Lista de Espera", len(lista_espera))
    m3.metric("Especialistas", len(especialistas_dict))

    st.divider()

    # 2. Pestañas Visuales (Sin código crudo)
    tab1, tab2, tab3 = st.tabs(["📅 Agenda de Turnos", "⏳ Lista de Espera", "👨‍⚕️ Cartilla Médica"])
    
    with tab1:
        if not turnos_dict:
            st.info("No hay turnos registrados en el sistema todavía.")
        else:
            # Transformamos el JSON en una tabla limpia para humanos
            filas_turnos = []
            for t_id, info in turnos_dict.items():
                nom_pac = pacientes_dict.get(info["paciente_id"], {}).get("nombre", info["paciente_id"])
                nom_esp = especialistas_dict.get(info["especialista_id"], {}).get("nombre", info["especialista_id"])
                retraso = info.get("metricas", {}).get("retraso_detectado_minutos", 0)
                
                filas_turnos.append({
                    "ID Turno": t_id,
                    "Paciente": nom_pac,
                    "Especialista": nom_esp,
                    "Fecha": info["fecha"],
                    "Hora": info["hora_estimada"],
                    "Estado": info["estado"].upper(),
                    "Demora (min)": f"+{retraso} min" if retraso > 0 else "A tiempo"
                })
            st.dataframe(filas_turnos, use_container_width=True, hide_index=True)

    with tab2:
        if not lista_espera:
            st.success("✅ No hay pacientes aguardando lugar en este momento.")
        else:
            st.dataframe(lista_espera, use_container_width=True, hide_index=True)

    with tab3:
        filas_esp = []
        for e_id, info in especialistas_dict.items():
            filas_esp.append({
                "Código": e_id,
                "Profesional": info["nombre"],
                "Especialidad": info["especialidad"],
                "Duración Turno": f"{info['duracion_base_minutos']} min",
                "Sobreturnos": "Sí" if info["permite_sobreturnos_urgencia"] else "No"
            })
        st.dataframe(filas_esp, use_container_width=True, hide_index=True)
