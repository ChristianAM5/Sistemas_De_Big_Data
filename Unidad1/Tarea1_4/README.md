# De imagen a CSV con OpenCV y Tesseract OCR

Proyecto académico (Sistemas de Big Data, Unidad 1, Tarea 1.4) que transforma un dato no estructurado (una imagen con texto) en datos estructurados (archivos TXT y CSV), utilizando técnicas de procesamiento de imágenes con OpenCV y reconocimiento óptico de caracteres (OCR) mediante PyTesseract y Tesseract.

El programa está diseñado para trabajar con imágenes de diferente naturaleza que contengan texto, como fotografías, documentos, capturas de pantalla o carteles.

## Características

- Lectura de imágenes en diferentes formatos, incluyendo imágenes con transparencia.
- Recorte opcional de una región concreta de la imagen antes de realizar el reconocimiento.
- Preprocesamiento configurable mediante eliminación de colores, conversión a escala de grises, ampliado y umbralizado.
- Reconocimiento de texto con Tesseract OCR utilizando el modo de segmentación de página `--psm 6`.
- Filtrado de palabras según el nivel mínimo de confianza establecido.
- Limpieza del texto reconocido para eliminar símbolos extraños, espacios innecesarios y líneas con ruido.
- Exportación del texto limpio a un archivo TXT y a un CSV estructurado por líneas.
- Guardado de la imagen preprocesada para comprobar visualmente el resultado.
- Visualización comparativa de la imagen original y la procesada.

## Tecnologías utilizadas

- Python 3.14 gestionado con [uv](https://docs.astral.sh/uv/).
- [opencv-python](https://pypi.org/project/opencv-python/) (procesamiento y preprocesamiento de imágenes).
- [numpy](https://pypi.org/project/numpy/) (carga y manipulación de imágenes).
- [pytesseract](https://pypi.org/project/pytesseract/) y [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (reconocimiento de texto).
- [Pillow](https://python-pillow.org/) (conversión y guardado de imágenes).
- [matplotlib](https://matplotlib.org/) (visualización de imágenes).

## Requisitos previos

- Python 3.14.
- uv instalado.
- Tesseract OCR instalado en el sistema:
  - Windows: mediante el instalador de [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
  - macOS: `brew install tesseract`.
  - Linux: `sudo apt install tesseract-ocr`.
- Idioma de reconocimiento instalado en Tesseract. Por defecto se utiliza inglés (`eng`).

## Instalación y configuración

1. Clona el repositorio y entra en la carpeta de la tarea:

   ```bash
   git clone https://github.com/ChristianAM5/Sistemas_De_Big_Data
   cd Unidad1/Tarea1_4
   ```

2. Instala las dependencias:

   ```bash
   uv sync
   ```

3. Coloca la imagen que quieras analizar en la misma carpeta que el script.

4. Abre el script y modifica las constantes del bloque `Configuración`, al principio del archivo:

   | Constante | Descripción |
   |---|---|
   | `RUTA_TESSERACT` | Ruta del ejecutable de Tesseract en tu equipo. |
   | `IMAGEN` | Ruta de la imagen que se quiere analizar. Por defecto, `Comentarios.jpg`. |
   | `NOMBRE_SALIDA` | Nombre base de los archivos generados. |
   | `RECORTE` | Coordenadas de la región que se quiere analizar. `None` procesa la imagen completa. |
   | `ESCALA` | Factor de ampliado de la imagen para facilitar el reconocimiento. |
   | `QUITAR_COLOR` | Elimina los colores con una saturación superior al límite establecido. |
   | `SATURACION_MAXIMA` | Umbral de saturación utilizado para eliminar colores. |
   | `USAR_UMBRAL` | Activa o desactiva la conversión a blanco y negro mediante Otsu. |
   | `CONFIANZA_MINIMA` | Nivel mínimo de confianza (0-100) para conservar una palabra reconocida. |
   | `IDIOMA` | Idioma utilizado por Tesseract (`eng`, `spa`, etc.). |
   | `MOSTRAR_IMAGENES` | Permite mostrar la imagen original y la procesada antes de continuar. |

   La configuración puede ajustarse dependiendo de las características de cada imagen. No todos los textos necesitan el mismo preprocesamiento, por lo que conviene probar diferentes valores si el reconocimiento no ofrece buenos resultados.

## Guía de uso

Ejecuta el programa desde la carpeta de la tarea:

```bash
uv run 1_4_Alvarez_Martinez_Christian.py
```

Si `MOSTRAR_IMAGENES` está activado, se abrirá una ventana con dos imágenes: la original y la procesada. Al cerrar la ventana, el programa continuará con el reconocimiento OCR.

Durante la ejecución se mostrarán por consola:

- El texto original obtenido directamente de Tesseract.
- El texto limpio después de aplicar los filtros y las correcciones de ruido.

Al finalizar, se creará una carpeta `resultados/` con los siguientes archivos:

- `1_4_Alvarez_Martinez_Christian.txt`: texto limpio reconocido por el OCR.
- `1_4_Alvarez_Martinez_Christian.csv`: texto limpio organizado por líneas.
- `1_4_Alvarez_Martinez_Christian_procesada.png`: imagen después del preprocesamiento.

Los nombres de los archivos dependen del valor configurado en `NOMBRE_SALIDA`.

## Cómo funciona

1. **Carga de la imagen:** se lee la imagen mediante OpenCV utilizando NumPy. También se contemplan imágenes en escala de grises y con transparencia, convirtiendo estas últimas a un fondo blanco.

2. **Preprocesamiento:** se aplican diferentes operaciones para mejorar la legibilidad del texto:
   - Recorte opcional de una región de interés.
   - Eliminación opcional de colores mediante el espacio de color HSV y un límite de saturación.
   - Conversión a escala de grises.
   - Ampliado de la imagen mediante interpolación cúbica.
   - Conversión a blanco y negro mediante el método de umbralización de Otsu.

3. **Visualización:** se muestra una comparación entre la imagen original y la procesada mediante Matplotlib, si esta opción está activada.

4. **Reconocimiento OCR:** PyTesseract utiliza Tesseract para extraer el texto de la imagen. Se emplea el modo de segmentación `--psm 6`, adecuado para bloques de texto. También se obtiene información adicional mediante `image_to_data`, que permite consultar la confianza de reconocimiento de cada palabra.

5. **Filtrado por confianza:** se descartan las palabras cuyo nivel de confianza sea inferior al mínimo configurado. Las palabras restantes se agrupan en líneas utilizando la información de bloque, párrafo y línea proporcionada por Tesseract.

6. **Limpieza del texto:** se eliminan símbolos no deseados, espacios repetidos, signos sueltos y líneas que no parecen contener texto significativo.

7. **Exportación:** el resultado limpio se guarda en un archivo TXT y en un CSV. Además, se guarda la imagen procesada para poder revisar el efecto de las operaciones aplicadas.

## Resultados

El programa genera tres archivos que permiten consultar y comprobar el resultado del procesamiento.

**Imagen después del preprocesamiento:**

![Imagen procesada](resultados/1_4_Alvarez_Martinez_Christian_procesada.png)

**Contenido del CSV generado:**

El CSV contiene dos columnas:

| Campo | Descripción |
|---|---|
| linea | Número de orden de la línea reconocida. |
| texto | Contenido de texto reconocido y limpiado. |

Ejemplo de su estructura:

| linea | texto |
|---|---|
| 1 | Primera línea reconocida |
| 2 | Segunda línea reconocida |
| 3 | Tercera línea reconocida |

**Archivo TXT:**

Contiene las mismas líneas de texto limpio que el CSV, pero en formato de texto plano, facilitando su lectura y revisión.

## Limitaciones

- La calidad del reconocimiento depende de la resolución de la imagen, la nitidez, el contraste, la iluminación y el tipo de letra.
- El preprocesamiento no garantiza una mejora en todos los casos. Por ejemplo, eliminar colores o aplicar umbralización puede perjudicar imágenes cuyo texto tenga poco contraste.
- El modo `--psm 6` está orientado a bloques de texto. Otras distribuciones pueden requerir una configuración diferente de Tesseract.
- El filtrado por confianza puede descartar palabras correctamente reconocidas si Tesseract les asigna una puntuación baja.
- La limpieza del texto puede eliminar información válida en determinados casos, especialmente cuando aparecen símbolos aislados o líneas muy cortas.
- El OCR puede cometer errores en textos manuscritos, tipografías poco habituales, imágenes de baja calidad o textos con elementos gráficos superpuestos.
- El reconocimiento depende de los idiomas instalados en Tesseract y de la configuración seleccionada.

## Estructura del proyecto

```text
Tarea1_4/
├── 1_4_Alvarez_Martinez_Christian.py   # Script principal
├── Comentarios.jpg                    # Imagen de entrada de ejemplo
├── resultados/
│   ├── 1_4_Alvarez_Martinez_Christian.txt
│   ├── 1_4_Alvarez_Martinez_Christian.csv
│   └── 1_4_Alvarez_Martinez_Christian_procesada.png
├── requirements.txt
└── README.md
```

## Autor

Christian Álvarez Martínez

## Licencia

Distribuido bajo la licencia [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html). Consulta el archivo `LICENSE` para más información.