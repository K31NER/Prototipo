import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from colorama import init, Fore
from .obtener_categoria import actualizar_categorias_meta

init(autoreset=True)

# --- Constantes ---
ARCHIVO_CACHE_CATEGORIAS = os.path.join("Clasificador/categorias.json")
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
TIMEOUT_REQUEST = 15

# --- NLP Ligero ---
STOPWORDS = {
    "de", "con", "para", "el", "la", "los", "las", "en", "y", "a", "por", "del", "un", "una", "15", "13", "inch", "''", '"', "”", "“"
}

def extraer_palabras_clave(texto):
    palabras = re.findall(r'\w+', texto.lower())
    return sorted(set(p for p in palabras if p not in STOPWORDS and len(p) > 2))

# --- Caché JSON ---
def cargar_cache_json(ruta):
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, dict):
                return {}
            return datos
        except Exception:
            return {}
    return {}

def guardar_cache_json(ruta, datos):
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(Fore.RED + f"Error guardando caché: {e}")

# --- Scraping de MercadoLibre ---
def obtener_categorias_mercadolibre(producto):
    print(Fore.CYAN + f"> Scrapeando categorías para '{producto}'...")
    delay = 5 + (os.getpid() % 5)  # entre 5 y 9 segundos dependiendo del PID
    print(Fore.CYAN + f"Esperado {delay} segundos...")
    time.sleep(delay)  # Esperar un tiempo aleatorio para evitar bloqueos
    url = f'https://listado.mercadolibre.com.co/{quote(producto)}'
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_REQUEST)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        selector = 'ol.andes-breadcrumb li.andes-breadcrumb__item span[itemprop="name"]'
        elementos = soup.select(selector)
        if not elementos:
            return ["Otras"]
        return [e.get_text(strip=True) for e in elementos if e.get_text(strip=True)]
    except:
        return ["Otras"]

# --- Coincidencia aproximada por palabras clave ---
def buscar_producto_similar(producto_clave, cache):
    clave_tokens = set(extraer_palabras_clave(producto_clave))
    mejor_match = None
    max_interseccion = 0

    for prod_cacheado in cache.keys():
        tokens_cacheado = set(extraer_palabras_clave(prod_cacheado))
        interseccion = len(clave_tokens & tokens_cacheado)
        if interseccion > max_interseccion:
            mejor_match = prod_cacheado
            max_interseccion = interseccion

    return mejor_match if max_interseccion >= 1 else None  # umbral mínimo (una palabra como minimo)

# --- Proceso General ---
def clasificar_producto(nombre_producto: str):
    producto_original = nombre_producto.strip()
    if not producto_original:
        return {"error": "Producto vacío."}

    producto_clave = producto_original.lower()
    datos_cache = cargar_cache_json(ARCHIVO_CACHE_CATEGORIAS)

    # 1. Buscar coincidencia exacta
    if producto_clave in datos_cache:
        print(Fore.GREEN + f"> Coincidencia exacta encontrada: '{producto_clave}'")
        return {"producto": producto_original, "categorias": datos_cache[producto_clave], "origen": "cache_exacto"}

    # 2. Buscar coincidencia aproximada por keywords
    similar = buscar_producto_similar(producto_clave, datos_cache)
    if similar:
        print(Fore.YELLOW + f"> Coincidencia aproximada encontrada con: '{similar}'")
        return {"producto": producto_original, "categorias": datos_cache[similar], "origen": f"cache_similar:{similar}"}

    # 3. Scraping y guardar
    print(Fore.CYAN + f"> No encontrado en caché. Procediendo a scraping.")
    categorias = obtener_categorias_mercadolibre(producto_original)
    datos_cache[producto_clave] = categorias
    guardar_cache_json(ARCHIVO_CACHE_CATEGORIAS, datos_cache)
    data =  {"producto": producto_original, "categorias": categorias, "origen": "scraping"}

    
    # 4. Registrar nueva categoría en el archivo meta (si aplica)
    if categorias and categorias[0]:
        categoria_meta = categorias[0]
        actualizar_categorias_meta(categoria_meta)
    
    return data
