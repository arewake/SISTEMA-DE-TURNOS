# database/firebase_db.py
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Ruta hacia el archivo de credenciales descargado de Firebase
CRED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "firebase_credentials.json")

def obtener_cliente_firestore():
    """Inicializa la conexión con Firebase y retorna el cliente de Firestore."""
    if not firebase_admin._apps:
        if not os.path.exists(CRED_PATH):
            raise FileNotFoundError(
                "❌ ERROR: No se encontró 'firebase_credentials.json' en la raíz del proyecto.\n"
                "Descárgalo desde Firebase Console > Configuración > Cuentas de servicio."
            )
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred)
    
    return firestore.client()

def inicializar_datos_clinica_firebase():
    """
    Si la base de datos en la nube está vacía, carga los especialistas
    y bloques laborales iniciales para que el sistema pueda operar.
    """
    db = obtener_cliente_firestore()
    
    # Verificar si ya existen especialistas cargados
    esp_ref = db.collection("especialistas")
    if len(list(esp_ref.limit(1).stream())) == 0:
        especialistas_iniciales = {
            "ESP_01": {
                "nombre": "Dr. Carlos Pérez",
                "especialidad": "Cardiología",
                "duracion_base_minutos": 20,
                "permite_sobreturnos_urgencia": True
            },
            "ESP_02": {
                "nombre": "Dra. Ana Gómez",
                "especialidad": "Psiquiatría",
                "duracion_base_minutos": 50,
                "permite_sobreturnos_urgencia": False
            }
        }
        for esp_id, datos in especialistas_iniciales.items():
            esp_ref.document(esp_id).set(datos)
            
        # Cargar bloque laboral inicial de ejemplo
        db.collection("bloques_disponibilidad").document("BLOQUE_01").set({
            "especialista_id": "ESP_01",
            "fecha": "2026-11-02",
            "hora_inicio": "09:00",
            "hora_fin": "13:00",
            "estado": "activo"
        })
        print("✅ Datos iniciales cargados en Firebase Firestore.")
