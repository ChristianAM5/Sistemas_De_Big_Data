import csv
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import cv2                              # Procesamiento de imagen
import numpy as np                      # Necesario para cargar la imagen de forma segura
import pytesseract                      # Conexión con Tesseract OCR
from matplotlib import pyplot as plt    # Para ver el resultado del preprocesado
from PIL import Image                   # pytesseract trabaja con imágenes PIL

# ----------------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------------

RUTA_TESSERACT = r"D:\Tesseract\tesseract.exe"

CARPETA = Path(__file__).resolve().parent
IMAGEN = CARPETA / "Gardevoir.png"
NOMBRE_BASE = "1_4_Alvarez_Martinez_Christian"
MOSTRAR_IMAGENES = True   # Abre ventanas con las zonas y el preprocesado (y guarda las imágenes en img/)
CARPETA_IMG = CARPETA / "img"
IDIOMA = "eng"

pytesseract.pytesseract.tesseract_cmd = RUTA_TESSERACT  # type: ignore

SOLO_DIGITOS = "--psm 7 -c tessedit_char_whitelist=0123456789"
SOLO_MULT = "--psm 7 -c tessedit_char_whitelist=x×-0123456789"


@dataclass
class Zona:
    """Una zona de la imagen y cómo preprocesarla y leerla."""
    caja: tuple[int, int, int, int]   # (fila1, fila2, columna1, columna2) en píxeles
    metodo: str = "gris"              # "gris" (sin umbral), "otsu" (automático),
                                      # "fijo" (umbral manual) o "adaptativo" (local)
    umbral: int = 0                   # solo se usa con metodo="fijo"
    escala: int = 3                   # factor de ampliado
    config: str = "--psm 7"           # opciones de Tesseract (7 = una línea, 6 = bloque)
    valida: str | None = None         # regex que debe cumplir el texto leído
    alternativas: list[dict] = field(default_factory=list)  # cambios a probar si no valida


ZONAS = {
    "nombre": Zona((25, 78, 165, 350), "fijo", 70, 4),
    "hp": Zona((38, 80, 462, 514), "fijo", 60, 4, SOLO_DIGITOS, r"\d{2,3}",
               [dict(umbral=50), dict(umbral=70), dict(escala=5)]),
    "evoluciona_de": Zona((78, 102, 110, 310), "otsu", 0, 3, "--psm 7", None,
                          [dict(metodo="gris")]),
    "regla_mega": Zona((498, 552, 95, 505), "gris", 0, 3, "--psm 6"),
    "ataque": Zona((578, 615, 160, 565), "gris", 0, 3, "--psm 7", r"[A-Za-z][A-Za-z' ]+ \d+\+?",
                   [dict(metodo="otsu"), dict(metodo="fijo", umbral=70, escala=4),
                    dict(metodo="adaptativo"), dict(escala=4, config="--psm 6")]),
    "descripcion": Zona((615, 697, 45, 565), "adaptativo", 0, 3, "--psm 6"),
    "debilidad": Zona((726, 750, 76, 112), "fijo", 60, 6, SOLO_MULT, r"[x×]\d+",
                      [dict(caja=(722, 752, 70, 120)), dict(umbral=50)]),
    "resistencia": Zona((724, 750, 180, 234), "fijo", 60, 6, SOLO_MULT, r"-\d+",
                        [dict(caja=(722, 752, 176, 238)), dict(umbral=50),
                         dict(caja=(722, 752, 176, 238), umbral=50), dict(umbral=70)]),
    "regla_ex": Zona((708, 778, 290, 565), "gris", 0, 3, "--psm 6"),
    "ilustrador": Zona((792, 822, 325, 445), "fijo", 70, 6),
    "numero_carta": Zona((792, 826, 438, 512), "fijo", 80, 5, "--psm 7 -c tessedit_char_whitelist=0123456789/",
                         r"\d+/\d+", [dict(umbral=100), dict(umbral=70), dict(escala=4)]),
}

# Errores típicos del OCR que corregimos a mano en la limpieza
CORRECCIONES = {"Pokemon": "Pokémon", "in-this": "in this", "this ways": "this way", "When I of": "When 1 of"}


# ----------------------------------------------------------------------------
# Imagen
# ----------------------------------------------------------------------------

def cargar_imagen(ruta: Path) -> np.ndarray:
    """Carga la imagen. Se hace con numpy porque cv2.imread falla con tildes en la ruta."""
    datos = np.fromfile(ruta, dtype=np.uint8)
    img = cv2.imdecode(datos, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"No se pudo leer la imagen: {ruta}")
    return img


def preprocesar_zona(img: np.ndarray, zona: Zona) -> np.ndarray:
    """Recorta una zona y la prepara para el OCR."""
    f1, f2, c1, c2 = zona.caja
    recorte = img[f1:f2, c1:c2]                               # recorte: [filas, columnas]
    gris = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)          # a escala de grises
    gris = cv2.resize(gris, None, fx=zona.escala, fy=zona.escala,
                      interpolation=cv2.INTER_CUBIC)          # ampliamos

    if zona.metodo == "fijo":
        # Todo lo más oscuro que el umbral pasa a negro (texto) y el resto a blanco
        _, gris = cv2.threshold(gris, zona.umbral, 255, cv2.THRESH_BINARY)
    elif zona.metodo == "otsu":
        _, gris = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif zona.metodo == "adaptativo":
        gris = cv2.medianBlur(gris, 3)                        # quita ruido
        gris = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 41, 15)

    # Margen blanco alrededor: Tesseract lee peor el texto pegado al borde
    return cv2.copyMakeBorder(gris, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)


def mostrar(img: np.ndarray, procesadas: dict) -> None:
    """Muestra (y guarda en img/) la carta con las zonas marcadas y cómo queda cada zona preprocesada."""
    CARPETA_IMG.mkdir(exist_ok=True)
    marcada = img.copy()
    for zona in ZONAS.values():
        f1, f2, c1, c2 = zona.caja
        cv2.rectangle(marcada, (c1, f1), (c2, f2), (0, 255, 0), 2)   # rectángulo verde
    plt.figure(figsize=(6, 8))
    plt.imshow(cv2.cvtColor(marcada, cv2.COLOR_BGR2RGB))             # OpenCV usa BGR, matplotlib RGB
    plt.title("Zonas de lectura")
    plt.axis("off")
    plt.savefig(CARPETA_IMG / "zonas_marcadas.png", dpi=150, bbox_inches="tight")

    fig, ejes = plt.subplots(len(procesadas), 1, figsize=(10, 1.4 * len(procesadas)))
    for eje, (campo, im) in zip(ejes, procesadas.items()):
        eje.imshow(im, cmap="gray")
        eje.set_title(campo, fontsize=8, loc="left")
        eje.axis("off")
    fig.suptitle("Imágenes preprocesadas (limpias)")
    plt.tight_layout()
    fig.savefig(CARPETA_IMG / "zonas_preprocesadas.png", dpi=150, bbox_inches="tight")
    plt.show()                                                       # cierra las ventanas para continuar


# ----------------------------------------------------------------------------
# 3. OCR
# ----------------------------------------------------------------------------

def reconocer_texto(procesada: np.ndarray, zona: Zona) -> str:
    """Convierte una zona procesada en texto."""
    pil_img = Image.fromarray(procesada)                     # array de numpy -> imagen PIL
    return pytesseract.image_to_string(pil_img, lang=IDIOMA, config=zona.config)


def leer_zona(img: np.ndarray, zona: Zona) -> str:
    """
    Lee una zona. Si tiene una regex 'valida' y el resultado no la cumple,
    prueba los ajustes alternativos hasta que alguno funcione.
    (Cada versión de Tesseract lee un poco distinto, así que esto da margen.)
    """
    intentos = [zona] + [replace(zona, **cambios) for cambios in zona.alternativas]
    primer_texto = ""
    for intento in intentos:
        texto = reconocer_texto(preprocesar_zona(img, intento), intento)
        if not zona.valida:
            return texto
        if re.fullmatch(zona.valida, re.sub(r"\s+", " ", texto).strip()):
            return texto                                     # cumple lo esperado
        primer_texto = primer_texto or texto                 # guardamos el primero no vacío
    return primer_texto


# ----------------------------------------------------------------------------
# 4. Limpieza y estructura
# ----------------------------------------------------------------------------

def proporcion_letras(linea: str) -> float:
    """Qué parte de la línea son letras (el ruido del OCR suele ser símbolos sueltos)."""
    sin_espacios = linea.replace(" ", "")
    return sum(c.isalpha() for c in sin_espacios) / len(sin_espacios) if sin_espacios else 0


def limpiar_bloque(texto: str, desde: str | None = None) -> str:
    """Limpia un texto de varias líneas: quita líneas basura, símbolos sobrantes y corrige errores."""
    lineas = []
    for linea in texto.splitlines():
        linea = re.sub(r"[^\w\s.,'’:;+%×/-]", " ", linea)         # quita símbolos raros
        linea = re.sub(r"\s+", " ", linea).strip()
        linea = re.sub(r"(?<=\w)[;:]$", ",", linea)               # pegada a una palabra, ; o : suele ser una coma mal leída
        linea = re.sub(r"[^\w.,]+$", "", linea)                    # quita basura al final de línea
        linea = re.sub(r"\s+(?![aAI]\b)\w$", "", linea)            # quita letra suelta final (ruido)
        # Nos quedamos solo con líneas que parecen texto real
        if len(linea.split()) >= 3 and proporcion_letras(linea) >= 0.75:
            lineas.append(linea)
    resultado = " ".join(lineas)

    if desde and desde in resultado:                               # descarta basura anterior a 'desde'
        resultado = resultado[resultado.index(desde):]
    resultado = resultado.rstrip(",;: ")
    # Quita palabras sueltas de 1-2 letras al final (restos de ruido)
    if not resultado.endswith("."):
        resultado = re.sub(r"(?:\s+\w{1,2})+$", "", resultado)
    for malo, bueno in CORRECCIONES.items():
        resultado = resultado.replace(malo, bueno)
    if resultado and not resultado.endswith("."):
        resultado += "."
    return resultado


def estructurar(crudo: dict) -> dict:
    """Convierte el texto en bruto de cada zona en un registro limpio."""
    def una_linea(campo: str) -> str:
        return re.sub(r"\s+", " ", crudo[campo]).strip()

    # Ataque: "Despair Ray 110+" -> nombre y daño por separado
    m = re.match(r"^(.*?)\s*(\d+\+?)$", una_linea("ataque"))
    nombre_ataque, danio = (m.group(1).strip(), m.group(2)) if m else (una_linea("ataque"), "")

    # En las cartas la resistencia siempre es negativa (-20, -30...): si el OCR perdió el "-", lo restituimos
    resistencia = una_linea("resistencia")
    if re.fullmatch(r"\d+", resistencia):
        resistencia = "-" + resistencia

    return {
        "nombre": re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", una_linea("nombre")),
        "hp": re.sub(r"\D", "", crudo["hp"]),
        "evoluciona_de": re.sub(r"\W+$", "", re.sub(r"^.*?\bfrom\s+", "", una_linea("evoluciona_de"))),
        "ataque": nombre_ataque,
        "danio": danio,
        "descripcion_ataque": limpiar_bloque(crudo["descripcion"]),
        "regla_mega": limpiar_bloque(crudo["regla_mega"], desde="When"),
        "regla_ex": limpiar_bloque(crudo["regla_ex"], desde="When"),
        "debilidad": una_linea("debilidad").replace("x", "×"),
        "resistencia": resistencia,
        "ilustrador": una_linea("ilustrador"),
        "numero_carta": una_linea("numero_carta"),
    }


# ----------------------------------------------------------------------------
# 5. CSV
# ----------------------------------------------------------------------------

def guardar_csv(registro: dict) -> Path:
    """Guarda el registro en un CSV: una fila con una columna por campo."""
    ruta = CARPETA / f"{NOMBRE_BASE}.csv"
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:   # utf-8-sig para que Excel lea bien tildes
        escritor = csv.DictWriter(archivo, fieldnames=list(registro.keys()))
        escritor.writeheader()
        escritor.writerow(registro)
    return ruta


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> None:
    print("[1/5] Cargando imagen...")
    img = cargar_imagen(IMAGEN)

    print("[2/5] Preprocesando zonas...")
    if MOSTRAR_IMAGENES:
        mostrar(img, {campo: preprocesar_zona(img, zona) for campo, zona in ZONAS.items()})

    print("[3/5] Reconociendo texto (OCR) zona a zona...")
    crudo = {campo: leer_zona(img, zona) for campo, zona in ZONAS.items()}
    # Guardamos el texto en bruto de cada zona para poder revisarlo
    with open(CARPETA / "ocr_bruto.txt", "w", encoding="utf-8") as f:
        for campo, texto in crudo.items():
            f.write(f"##### {campo}\n{texto}\n")

    print("[4/5] Estructurando texto...")
    registro = estructurar(crudo)
    for campo, valor in registro.items():
        print(f"      {campo:20s} -> {valor}")

    print("[5/5] Guardando CSV...")
    print(f"      CSV: {guardar_csv(registro)}")


if __name__ == "__main__":
    main()