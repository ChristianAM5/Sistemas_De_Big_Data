import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from atproto import Client
from dotenv import load_dotenv
from google import genai
from pymongo import MongoClient

# Configuración
# Cargamos las variables del .env
load_dotenv()

BSKY_IDENTIFIER = os.getenv("BSKY_IDENTIFIER")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PERFIL_URL = "https://bsky.app/profile/elpais.com"
PERFIL = PERFIL_URL.rstrip("/").split("/")[-1]  # nos quedamos solo con elpais.com
LIMITE_POSTS = 50  # máximo permitido por petición: 100

MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "bluesky_analisis"
MONGO_COLLECTION = "feeds"

MODELO_GEMINI = "gemini-3.8-flash"

# Nombre base de los archivos de entrega (.txt y .json)
NOMBRE_BASE = "1_3_Alvarez_Martinez_Christian"
# Carpeta donde está este script: ahí se guardarán los archivos de salida
CARPETA_SALIDA = Path(__file__).resolve().parent

# Bluesky

def conectar_bluesky() -> Client:
    """Inicia sesión en Bluesky y devuelve el cliente."""
    if not BSKY_IDENTIFIER or not BSKY_PASSWORD:
        raise RuntimeError("Faltan BSKY_IDENTIFIER o BSKY_PASSWORD en el .env")
    client = Client()
    client.login(BSKY_IDENTIFIER, BSKY_PASSWORD)
    return client


# Patrón para detectar emojis y símbolos
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # pictogramas y emoticonos
    "\U00002600-\U000027BF"  # símbolos varios
    "\U0001F1E6-\U0001F1FF"  # banderas
    "\U0000FE0F\U0000200D"   # selector de variación 
    "]+",
    flags=re.UNICODE,
)
# Patrón que detecta enlaces
URL_RE = re.compile(r"https?://\S+|www\.\S+")

# Borrar enlaces, emojis y quitar espacios
def limpiar_texto(texto: str) -> str:
    """Elimina URLs, emojis y espacios sobrantes."""
    texto = URL_RE.sub("", texto)
    texto = EMOJI_RE.sub("", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def obtener_feed(client: Client, actor: str, limit: int) -> list[dict]:
    """Descarga el feed de un perfil y devuelve una lista de posts limpios."""
    respuesta = client.get_author_feed(actor=actor, limit=limit)
    posts = []

    for item in respuesta.feed:
        # Descartamos reposts de otras cuentas, solo queremos contenido propio del perfil
        if item.reason is not None:
            continue

        post = item.post
        # Texto del post (si no hubiera, usamos cadena vacía)
        texto_original = getattr(post.record, "text", "") or ""
        texto_limpio = limpiar_texto(texto_original)
        # Si tras limpiar no queda nada (ej. solo imagen o enlace), lo descartamos
        if not texto_limpio:
            continue

        # Guardamos una "ficha" con los datos útiles de cada post
        posts.append(
            {
                "uri": post.uri,
                "fecha": getattr(post.record, "created_at", None),
                "texto_original": texto_original,
                "texto_limpio": texto_limpio,
                "likes": post.like_count,
                "reposts": post.repost_count,
                "respuestas": post.reply_count,
            }
        )
    return posts


# MongoDB

def guardar_feed_en_mongo(coleccion, perfil: str, posts: list[dict]):
    """Inserta el documento del feed (aún sin análisis) y devuelve su _id."""
    documento = {
        "perfil": perfil,
        "url": PERFIL_URL,
        "fecha_extraccion": datetime.now(timezone.utc),
        "num_posts": len(posts),
        "posts": posts,
        "analisis_llm": None,
        "modelo_llm": None,
    }
    return coleccion.insert_one(documento).inserted_id


def guardar_analisis_en_mongo(coleccion, doc_id, analisis: str) -> None:
    """Asocia el análisis del LLM al documento del feed."""
    # Busca el documento por su _id y rellena los campos del análisis
    coleccion.update_one(
        {"_id": doc_id},
        {"$set": {"analisis_llm": analisis, "modelo_llm": MODELO_GEMINI}},
    )

# Gemini

def construir_prompt(perfil: str, posts: list[dict]) -> str:
    contexto = (
        f"Eres un analista de redes sociales y medios de comunicación. "
        f"A continuación te proporciono los últimos {len(posts)} posts publicados "
        f"en Bluesky por la cuenta '{perfil}'. Los textos ya han sido limpiados "
        f"(sin URLs ni emojis). Analízalos en conjunto.\n\n"
        f"=== FEED ===\n"
    )

    # Un post por línea numerados
    feed = "\n".join(f"{i}. {p['texto_limpio']}" for i, p in enumerate(posts, start=1))

    formato = (
        "\n\n=== FORMATO DE RESPUESTA ===\n"
        "Responde en español, con texto claro y estas secciones:\n"
        "1. Resumen general del perfil (2-3 frases).\n"
        "2. Temas principales (lista con los 5 temas más frecuentes).\n"
        "3. Tono y estilo de comunicación.\n"
        "4. Sentimiento general (positivo, neutro o negativo) con justificación breve.\n"
        "5. Conclusiones: qué tipo de audiencia y objetivo parece tener la cuenta.\n"
        "Sé conciso y basa tus afirmaciones únicamente en los posts proporcionados."
    )
    return contexto + feed + formato


def analizar_con_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("Falta GEMINI_API_KEY en el .env")
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model=MODELO_GEMINI, contents=prompt)
    if not response.text:
        raise RuntimeError("Gemini no devolvió texto (posible bloqueo o respuesta vacía).")
    return response.text


# Salidas (TXT y JSON)

def guardar_txt(analisis: str) -> Path:
    ruta = CARPETA_SALIDA / f"{NOMBRE_BASE}.txt"
    ruta.write_text(analisis, encoding="utf-8")
    return ruta


def exportar_json(coleccion, doc_id) -> Path:
    documento = coleccion.find_one({"_id": doc_id})
    ruta = CARPETA_SALIDA / f"{NOMBRE_BASE}.json"
    # default=str convierte tipos que JSON no entiende (ObjectId, fechas) a texto
    ruta.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return ruta


# Main

def main() -> None:
    print(f"[1/5] Conectando a Bluesky y descargando feed de {PERFIL}...")
    bsky = conectar_bluesky()
    posts = obtener_feed(bsky, PERFIL, LIMITE_POSTS)
    if not posts:
        raise SystemExit("No se obtuvieron posts con texto del perfil.")
    print(f"      {len(posts)} posts obtenidos y limpiados.")

    print("[2/5] Guardando feed en MongoDB...")
    mongo = MongoClient(MONGO_URI)
    coleccion = mongo[MONGO_DB][MONGO_COLLECTION]
    doc_id = guardar_feed_en_mongo(coleccion, PERFIL, posts)

    print(f"[3/5] Enviando datos a Gemini ({MODELO_GEMINI})...")
    prompt = construir_prompt(PERFIL, posts)
    analisis = analizar_con_gemini(prompt)

    print("[4/5] Guardando análisis en MongoDB...")
    guardar_analisis_en_mongo(coleccion, doc_id, analisis)

    print("[5/5] Generando archivos de salida...")
    ruta_txt = guardar_txt(analisis)
    ruta_json = exportar_json(coleccion, doc_id)
    print(f"      TXT : {ruta_txt}")
    print(f"      JSON: {ruta_json}")

    print("\n===== ANÁLISIS =====\n")
    print(analisis)


if __name__ == "__main__":
    main()