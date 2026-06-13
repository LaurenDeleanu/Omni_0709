import os
import json
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Asegurar que .env está cargado
load_dotenv()

# Definimos las herramientas (Function Calling) que le damos a OpenAI
# En este caso, le decimos a la IA que queremos que estructure su respuesta en un JSON específico.
tools = [
    {
        "type": "function",
        "function": {
            "name": "generate_module_metadata",
            "description": "Genera los metadatos necesarios para construir dinámicamente un módulo y una página en la plataforma. Devuelve el schema (SchemaNode) en formato JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "El nombre corto del módulo, en minúsculas y sin espacios (ej. 'rrhh', 'ventas', 'vacaciones')."
                    },
                    "page_name": {
                        "type": "string",
                        "description": "El nombre corto de la página dentro del módulo, en minúsculas y sin espacios (ej. 'solicitudes', 'dashboard')."
                    },
                    "description": {
                        "type": "string",
                        "description": "Una breve descripción del propósito de la página generada."
                    },
                    "schema_data": {
                        "type": "object",
                        "description": "El árbol de SchemaNode. Debe empezar SIEMPRE con un nodo root de type 'page'. Debe contener id (preferible 'root'), type, props y children.",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string", "enum": ["page", "layout", "form", "table", "text", "card"]},
                            "props": {"type": "object"},
                            "children": {
                                "type": "array",
                                "items": {"type": "object"}
                            }
                        },
                        "required": ["id", "type", "props"]
                    }
                },
                "required": ["module_name", "page_name", "description", "schema_data"]
            }
        }
    }
]


def _get_client():
    """Lazy-load del cliente OpenAI para que la key se lea DESPUÉS de cargar .env."""
    
    from openai import AsyncOpenAI
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None, ""
    return AsyncOpenAI(api_key=api_key), api_key


async def generate_dynamic_page(prompt: str):
    """
    Toma un prompt en lenguaje natural, llama a OpenAI, y devuelve
    la metadata estructurada.
    """
    client, api_key = _get_client()

    # Si estamos en modo de prueba o sin API KEY, devolvemos un mock
    if not client or not api_key:
        logger.warning("No se ha configurado OPENAI_API_KEY. Usando Mock de IA.")
        return {
            "module_name": "demo",
            "page_name": "ai-test",
            "description": "Página generada de prueba (Mock)",
            "schema_data": {
                "id": "root",
                "type": "page",
                "props": {
                    "title": "Página Generada por IA (Mock)",
                    "description": f"Has pedido: {prompt}"
                },
                "children": [
                    {
                        "id": "mock-layout-1",
                        "type": "layout",
                        "props": {"direction": "column", "padding": 20},
                        "children": [
                            {
                                "id": "mock-text-1",
                                "type": "text",
                                "props": {"text": "Añade tu clave OPENAI_API_KEY en el .env del backend para generar contenido real.", "fontSize": 16}
                            }
                        ]
                    }
                ]
            }
        }

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente de IA para una plataforma SaaS. Tu objetivo es interpretar la petición del usuario y generar la metadata de un módulo dinámico, componiendo interfaces con contenedores (layout), textos (text), formularios (form) y tablas (table)."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "generate_module_metadata"}},
            temperature=0.7,
        )

        # Extraer el JSON generado por el LLM
        tool_call = response.choices[0].message.tool_calls[0]
        arguments_str = tool_call.function.arguments
        
        # Parsear el string a diccionario de Python
        metadata = json.loads(arguments_str)
        return metadata

    except Exception as e:
        logger.error(f"Error llamando a OpenAI: {e}")
        # Si es un error de cuota (429) o credenciales, devolvemos un Mock amigable para no bloquear el flujo
        if "insufficient_quota" in str(e) or "429" in str(e) or "401" in str(e):
            logger.warning("Fallo de API Key de OpenAI (sin saldo o inválida). Retornando Mock.")
            return {
                "module_name": "demo-mock",
                "page_name": "ai-fallback",
                "description": "Página generada de prueba (Fallback por error de cuota)",
                "schema_data": {
                    "id": "root",
                    "type": "page",
                    "props": {
                        "title": "Fallback: Error de Saldo en OpenAI",
                        "description": f"Has pedido: {prompt}. (Nota: Tu API Key no tiene saldo, por lo que mostramos esta demo)."
                    },
                    "children": [
                        {
                            "id": "fallback-layout",
                            "type": "layout",
                            "props": {"direction": "column", "padding": 20},
                            "children": [
                                {
                                    "id": "fallback-text",
                                    "type": "text",
                                    "props": {"text": "Tu clave de OpenAI no tiene saldo disponible o ha expirado. Por favor, recarga tu cuenta de OpenAI para generar contenido real.", "fontSize": 16}
                                }
                            ]
                        }
                    ]
                }
            }
        
        raise ValueError(f"Error generando contenido con IA: {str(e)}")

