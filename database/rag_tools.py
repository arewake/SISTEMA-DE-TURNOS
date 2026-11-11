# database/rag_tools.py
import json
import os
from crewai.tools import tool

MANUAL_PATH = os.path.join(os.path.dirname(__file__), "manual_clinica.json")

@tool("Consultar Manual y Políticas de la Clínica")
def tool_consultar_rag_clinica(consulta: str) -> str:
    """
    Busca información oficial sobre preparación de estudios médicos, obras sociales aceptadas,
    tolerancia de demoras y políticas de cancelación de la clínica.
    Úsala siempre que el paciente pregunte sobre requisitos, estudios o reglas administrativas.
    """
    try:
        if not os.path.exists(MANUAL_PATH):
            return "Error interno: No se encontró el archivo del manual de la clínica."
            
        with open(MANUAL_PATH, "r", encoding="utf-8") as f:
            manual = json.load(f)
            
        consulta_lower = consulta.lower()
        resultados = []
        
        # Recorremos las categorías del manual buscando coincidencias relevantes
        for categoria, items in manual.items():
            for clave, contenido in items.items():
                # Si la clave o palabras de la consulta coinciden con el contenido
                if clave in consulta_lower or any(palabra in contenido.lower() for palabra in consulta_lower.split() if len(palabra) > 3):
                    resultados.append(f"[{categoria.upper()} - {clave}]: {contenido}")
                    
        if not resultados:
            # Si no hay coincidencia exacta, devolvemos todo el manual (es pequeño) para que Gemini extraiga la respuesta
            return f"Información general de la clínica disponible:\n{json.dumps(manual, indent=2, ensure_ascii=False)}"
            
        return "Información oficial encontrada en el manual:\n" + "\n".join(resultados)
        
    except Exception as e:
        return f"Error al consultar el manual de la clínica: {str(e)}"
