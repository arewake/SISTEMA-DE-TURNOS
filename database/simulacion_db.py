# database/simulacion_db.py
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "clinica_mock.json")

def obtener_datos_iniciales():
    """Define la estructura base y elástica de nuestra clínica moderna."""
    return {
        "especialistas": {
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
        },
        "pacientes": {
            "PAC_101": {
                "nombre": "Juan Pérez",
                "telefono": "+5491122334455",
                "historial_ausencias": 0
            }
        },
        "bloques_disponibilidad": {
            "BLOQUE_01": {
                "especialista_id": "ESP_01",
                "fecha": "2026-11-02",
                "hora_inicio": "09:00",
                "hora_fin": "13:00",
                "estado": "activo"
            }
        },
        "turnos": {},
        "lista_espera_dinamica": []
    }

def cargar_db():
    """Carga los datos desde el archivo JSON simulado."""
    if not os.path.exists(DB_PATH):
        guardar_db(obtener_datos_iniciales())
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_db(data):
    """Guarda el estado actual de la clínica en el archivo JSON."""
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)