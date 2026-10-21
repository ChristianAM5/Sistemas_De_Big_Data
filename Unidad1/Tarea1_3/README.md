# Análisis de un perfil de Bluesky con Gemini

Proyecto académico (Sistemas de Big Data, Unidad 1, Tarea 1.3) que extrae los posts de un perfil de Bluesky, los almacena en MongoDB y genera un análisis del contenido usando la API de Gemini.

## Características

- Descarga el feed de un perfil de Bluesky (por defecto, `elpais.com`).
- Limpia los textos (elimina URLs, emojis y espacios sobrantes) y descarta reposts.
- Guarda el feed en MongoDB y le asocia el análisis generado por el LLM.
- Exporta el análisis a un `.txt` y el documento de Mongo a un `.json`.

## Tecnologías utilizadas

- Python 3.14 gestionado con [uv](https://docs.astral.sh/uv/)
- [atproto](https://atproto.blue/) (SDK de Bluesky)
- [google-genai](https://ai.google.dev/gemini-api/docs) (API de Gemini)
- [pymongo](https://pymongo.readthedocs.io/) y MongoDB
- [python-dotenv](https://pypi.org/project/python-dotenv/)

## Requisitos previos

- uv instalado
- MongoDB en ejecución en local (`mongodb://localhost:27017/`)
- Cuenta de Bluesky con una contraseña de app
- Clave de la API de Gemini

## Instalación y configuración

1. Clona el repositorio y entra en la carpeta de la tarea:
   ```bash
   git clone <url-del-repositorio>
   cd <carpeta_asignatura>/<carpeta_unidad1>/<carpeta_tarea1.3>
   ```
2. Instala las dependencias:
   ```bash
   uv sync
   ```
   (o, alternativamente, `uv pip install -r requirements.txt`)
3. Crea un archivo `.env` en la misma carpeta que el script, con tus credenciales:
   ```dotenv
   BSKY_IDENTIFIER=tu_handle_o_email
   BSKY_PASSWORD=tu_contraseña_de_app
   GEMINI_API_KEY=tu_clave_de_gemini
   ```
   El archivo `.env` está en el `.gitignore` y no debe subirse al repositorio.

## Guía de uso

```bash
uv run 1_3_Alvarez_Martinez_Christian.py
```

El script realiza estos pasos:

1. Inicia sesión en Bluesky y descarga el feed de `elpais.com`.
2. Guarda los posts limpios en la colección `feeds` de la base de datos `bluesky_analisis`.
3. Envía el feed a Gemini y recibe el análisis.
4. Guarda el análisis en el documento de Mongo y genera los archivos de salida.

Para cambiar el perfil o el número de posts, edita las constantes `PERFIL_URL` y `LIMITE_POSTS` al inicio del script.

## Estructura del proyecto

```
Tarea1_3/
├── 1_3_Alvarez_Martinez_Christian.py    # Script principal
├── 1_3_Alvarez_Martinez_Christian.txt   # Análisis generado por Gemini
├── 1_3_Alvarez_Martinez_Christian.json  # Documento de MongoDB
├── requirements.txt
└── README.md
```

## Autor

Christian Álvarez Martínez

## Licencia

Distribuido bajo la licencia GPL-3,0 Consulta el archivo `LICENSE` para más información.
