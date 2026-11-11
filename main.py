# main.py
import json
from crewai import Crew, Process, Task
from database.simulacion_db import cargar_db, guardar_db, DB_PATH

# Importar los constructores de nuestros agentes
from agents.notificador import crear_agente_seguimiento

def preparar_escenario_cancelacion():
    """Fuerza un estado inicial en la base de datos para la simulación."""
    db = cargar_db()
    
    # 1. Creamos un turno confirmado que luego será cancelado
    db["turnos"]["TURNO_PREVIO_123"] = {
        "paciente_id": "PAC_101",
        "especialista_id": "ESP_01",
        "fecha": "2026-11-02",
        "hora_estimada": "10:00",
        "duracion_asignada_minutos": 20,
        "estado": "confirmado",
        "bloqueado_hasta": None
    }
    
    # 2. Poblamos la lista de espera dinámica con un paciente rezagado
    db["lista_espera_dinamica"] = [
        {
            "paciente_id": "PAC_999",
            "motivo": "Control post-operatorio urgente",
            "prioridad": "alta"
        }
    ]
    
    guardar_db(db)
    print("🏥 Estado inicial de la clínica cargado (Turno existente y Lista de espera activa).")

def simular_optimizacion_agenda():
    # Configurar el escenario base
    preparar_escenario_cancelacion()
    
    # 1. Instanciar al agente de seguimiento
    agente_seguimiento = crear_agente_seguimiento()
    
    # ID del turno que el paciente ficticio va a cancelar por WhatsApp
    id_turno_a_cancelar = "TURNO_PREVIO_123"
    
    # 2. Definir las tareas consecutivas de optimización
    task_procesar_cancelacion = Task(
        description=(
            f"El paciente dueño del turno '{id_turno_a_cancelar}' ha enviado un mensaje avisando "
            "que no podrá asistir. Utiliza tu herramienta 'Procesar Cancelación y Liberar Espacio' "
            "para liberar ese turno en el sistema de manera inmediata."
        ),
        expected_output="Confirmación del éxito de la cancelación detallando el especialista, fecha y hora que quedaron libres.",
        agent=agente_seguimiento
    )
    
    task_rellenar_hueco = Task(
        description=(
            "Inmediatamente después de haber cancelado el turno anterior, revisa los detalles del hueco "
            "que acaba de quedar libre (Especialista, Fecha y Hora). Ejecuta de forma proactiva la herramienta "
            "'Consultar y Asignar Lista de Espera' para verificar si hay pacientes esperando y reubicar al "
            "primer candidato disponible en ese espacio vacío."
        ),
        expected_output="El resultado de la asignación del nuevo paciente de la lista de espera al espacio liberado.",
        agent=agente_seguimiento,
        dependencies=[task_procesar_cancelacion]
    )

    # 3. Agrupar en la tripulación de CrewAI
    notificador_crew = Crew(
        agents=[agente_seguimiento],
        tasks=[task_procesar_cancelacion, task_rellenar_hueco],
        process=Process.sequential,
        verbose=True
    )
    
    # 4. Correr la simulación en tiempo real
    print("\n🚀 El Agente Notificador ha detectado un evento de cancelación. Iniciando optimización...")
    resultado_final = notificador_crew.kickoff()
    
    # 5. Mostrar los resultados finales en la BD para comprobar la persistencia
    print("\n📊 --- COMPROBACIÓN DE LA BASE DE DATOS LOCAL ---")
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db_final = json.load(f)
        
    print(f"Estado final del turno TURNO_PREVIO_123: {db_final['turnos']['TURNO_PREVIO_123']['estado']}")
    print(f"Pacientes remanentes en lista de espera: {len(db_final['lista_espera_dinamica'])}")
    print("\n📝 RESUMEN DE ACCIONES DEL AGENTE:")
    print(resultado_final)

if __name__ == "__main__":
    simular_optimizacion_agenda()
