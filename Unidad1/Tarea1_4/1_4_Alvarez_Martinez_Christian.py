import csv
import re
import shutil
from pathlib import Path

import cv2                              # Procesamiento de imagen
import numpy as np                      # Para cargar la imagen
import pytesseract                      # Conexión con Tesseract OCR
from matplotlib import pyplot as plt    # Para ver el resultado del procesado
from PIL import Image                   # pytesseract trabaja con imágenes PIL

# ----------------------------------------------------------------------------
# Configuración (lo que puedes modificar)
# ----------------------------------------------------------------------------

# Ruta del ejecutable de Tesseract en tu equipo
RUTA_TESSERACT = r"D:\Tesseract\tesseract.exe"

CARPETA = Path(__file__).resolve().parent
IMAGEN = CARPETA / "Comentarios.jpg"               # imagen a analizar (en la misma carpeta que el script)
NOMBRE_SALIDA = "1_4_Alvarez_Martinez_Christian"  # nombre de los archivos de salida

# Recorte de la zona a leer: (fila1, fila2, columna1, columna2). None = imagen entera.
RECORTE: tuple[int, int, int, int] | None = None
ESCALA = 3              # factor de ampliado (el OCR lee mejor el texto grande)
QUITAR_COLOR = False     # borra los colores vivos antes de leer; poner en False si la imagen es a todo color
SATURACION_MAXIMA = 90  # 0-255: lo que tenga más color que esto se borra (valor más bajo = borra más color)
USAR_UMBRAL = True      # pasa la imagen a blanco y negro; ponlo en False si la imagen sale peor
CONFIANZA_MINIMA = 50   # 0-100: se descartan las palabras que Tesseract lee con menos seguridad
IDIOMA = "eng"          # idioma del texto de la imagen ("spa" español, "eng" inglés...); debe estar instalado en Tesseract
MOSTRAR_IMAGENES = True # abre una ventana con el antes/después

pytesseract.pytesseract.tesseract_cmd = RUTA_TESSERACT  # type: ignore


# ----------------------------------------------------------------------------
# 1. Cargar imagen
# ----------------------------------------------------------------------------
def cargar_imagen(ruta: Path) -> np.ndarray:
    """Carga la imagen. Si es un PNG con transparencia, la transparencia pasa a fondo blanco."""
    datos = np.fromfile(ruta, dtype=np.uint8)           # (cv2.imread falla con tildes en la ruta)
    img = cv2.imdecode(datos, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"No se pudo leer la imagen: {ruta}")
    if img.ndim == 2:                                   # imagen en gris -> 3 canales
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:                             # con canal alfa (transparencia)
        alfa = img[:, :, 3:4] / 255.0
        img = (img[:, :, :3] * alfa + 255 * (1 - alfa)).astype(np.uint8)
    return img


# ----------------------------------------------------------------------------
# 2. Preprocesado
# ----------------------------------------------------------------------------
def preprocesar(img: np.ndarray) -> np.ndarray:
    """Recorta, quita colores, pasa a gris, amplía y convierte a blanco y negro."""
    if RECORTE:
        f1, f2, c1, c2 = RECORTE
        img = img[f1:f2, c1:c2]                         # recorte: [filas, columnas]
    if QUITAR_COLOR:
        # Los colores vivos (rojo, verde...) tienen mucha saturación; el texto negro y el gris, muy poca
        saturacion = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1]
        img = img.copy()
        img[saturacion > SATURACION_MAXIMA] = 255       # lo coloreado pasa a blanco
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)        # escala de grises
    gris = cv2.resize(gris, None, fx=ESCALA, fy=ESCALA, interpolation=cv2.INTER_CUBIC)
    if USAR_UMBRAL:
        # Otsu elige solo el umbral: lo claro pasa a blanco y lo oscuro a negro
        _, gris = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return gris


def mostrar(original: np.ndarray, procesada: np.ndarray) -> None:
    """Muestra la imagen original y la procesada lado a lado."""
    fig, ejes = plt.subplots(1, 2, figsize=(14, 6))
    ejes[0].imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))   # OpenCV usa BGR, matplotlib RGB
    ejes[0].set_title("Original")
    ejes[1].imshow(procesada, cmap="gray")
    ejes[1].set_title("Imagen preprocesada (limpia)")
    for eje in ejes:
        eje.axis("off")
    plt.tight_layout()
    plt.show()


# ----------------------------------------------------------------------------
# 3. OCR
# ----------------------------------------------------------------------------
def reconocer(procesada: np.ndarray) -> tuple[str, list[str]]:
    """Devuelve (texto en bruto, líneas con solo las palabras de confianza suficiente)."""
    pil_img = Image.fromarray(procesada)                # array de numpy -> imagen PIL
    config = "--psm 6"                                  # 6 = bloque de texto con varias líneas

    texto_bruto = pytesseract.image_to_string(pil_img, lang=IDIOMA, config=config)

    # image_to_data da, además del texto, la confianza (0-100) de cada palabra
    datos = pytesseract.image_to_data(pil_img, lang=IDIOMA, config=config,
                                      output_type=pytesseract.Output.DICT)
    lineas: dict[tuple, list[str]] = {}
    for i, palabra in enumerate(datos["text"]):
        palabra = palabra.strip()
        if palabra and float(datos["conf"][i]) >= CONFIANZA_MINIMA:
            clave = (datos["block_num"][i], datos["par_num"][i], datos["line_num"][i])
            lineas.setdefault(clave, []).append(palabra)   # agrupamos las palabras por línea
    return texto_bruto, [" ".join(palabras) for palabras in lineas.values()]


# ----------------------------------------------------------------------------
# 4. Limpieza
# ----------------------------------------------------------------------------
def limpiar(lineas: list[str]) -> list[str]:
    """Quita símbolos raros y descarta las líneas que no parecen texto."""
    limpias = []
    for linea in lineas:
        linea = re.sub(r"[^\w\s.,'’:;()%+×/-]", " ", linea)   # quita símbolos raros
        linea = re.sub(r"\s+", " ", linea).strip()             # espacios múltiples -> uno
        linea = re.sub(r"^[-_.,;:\s]+", "", linea)             # quita signos sueltos al principio
        linea = re.sub(r"^(?![aAI1]\b)\w\s+", "", linea)       # quita letra suelta al principio
        linea = re.sub(r"\s+(?![aAI]\b)\w$", "", linea)        # quita letra suelta al final
        # Una línea de texto real tiene una palabra de 4 letras o más, o al menos 3 palabras de 2 letras o más
        letras = [sum(c.isalpha() for c in p) for p in linea.split()]
        if any(n >= 4 for n in letras) or sum(n >= 2 for n in letras) >= 3:
            limpias.append(linea)
    return limpias


# ----------------------------------------------------------------------------
# 5. Guardar
# ----------------------------------------------------------------------------
def guardar(lineas: list[str], procesada: np.ndarray) -> None:
    """Guarda el texto (TXT), una tabla línea/texto (CSV) y la imagen procesada."""
    carpeta = CARPETA / "resultados"
    carpeta.mkdir(exist_ok=True)

    (carpeta / f"{NOMBRE_SALIDA}.txt").write_text("\n".join(lineas), encoding="utf-8")

    with open(carpeta / f"{NOMBRE_SALIDA}.csv", "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f)
        escritor.writerow(["linea", "texto"])
        for n, linea in enumerate(lineas, start=1):
            escritor.writerow([n, linea])

    Image.fromarray(procesada).save(carpeta / f"{NOMBRE_SALIDA}_procesada.png")
    print(f"Resultados guardados en: {carpeta}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> None:
    if not shutil.which(RUTA_TESSERACT):
        raise SystemExit(f"No se encuentra Tesseract ('{RUTA_TESSERACT}'). "
                         "Instálalo y corrige la constante RUTA_TESSERACT al principio del script.")

    if IDIOMA not in pytesseract.get_languages(config=""):
        raise SystemExit(f"Tesseract no tiene instalado el idioma '{IDIOMA}'. Instálalo "
                         "(en Windows, el archivo .traineddata va en la carpeta tessdata) o cambia IDIOMA.")

    original = cargar_imagen(IMAGEN)
    procesada = preprocesar(original)
    if MOSTRAR_IMAGENES:
        mostrar(original, procesada)         # cierra la ventana para que el script continúe

    texto_bruto, lineas = reconocer(procesada)
    print("===== TEXTO EN BRUTO =====")
    print(texto_bruto)

    resultado = limpiar(lineas)
    print("===== TEXTO LIMPIO =====")
    print("\n".join(resultado))

    guardar(resultado, procesada)


if __name__ == "__main__":
    main()
