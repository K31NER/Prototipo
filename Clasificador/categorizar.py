import os
import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import quote 
from colorama import init, Fore, Back, Style

# Inicializar colorama (necesario en Windows)
init(autoreset=True)

# --- Constantes ---
# Asegúrate de que la carpeta 'modelo/Clasificador' exista o ajusta la ruta
DIRECTORIO_JSON = "modelo/Clasificador"
ARCHIVO_JSON = os.path.join(DIRECTORIO_JSON, "categorias_sinonimos.json")
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# --- Funciones de Scraping ---

def obtener_categorias(producto):
    """Obtiene las categorías de un producto desde Mercado Libre."""
    print(Fore.CYAN + f"--- Intentando obtener categorías para '{producto}' desde Mercado Libre...")
    url_pagina = f'https://listado.mercadolibre.com.co/{quote(producto)}'
    headers = {'User-Agent': USER_AGENT}
    categorias = []

    try:
        response = requests.get(url_pagina, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        selector_categorias = 'ol.andes-breadcrumb li.andes-breadcrumb__item span[itemprop="name"]'
        elementos_categoria = soup.select(selector_categorias)

        if not elementos_categoria:
            print(Fore.YELLOW + f"Advertencia: No se encontraron elementos de categoría para '{producto}'.")
            # Podrías devolver ["Otras"] aquí si prefieres ese valor por defecto
        else:
            for elemento in elementos_categoria:
                nombre_categoria = elemento.get_text(strip=True)
                if nombre_categoria:
                    categorias.append(nombre_categoria)
            if categorias:
                 print(Fore.GREEN + "Categorías encontradas:", Style.BRIGHT + " -> ".join(categorias))
            else:
                 print(Fore.YELLOW + f"Se encontraron elementos, pero no se pudo extraer texto de categoría para '{producto}'.")


    except requests.exceptions.Timeout:
        print(Fore.RED + f"Error: Timeout al obtener categorías para '{producto}'.")
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error en la solicitud HTTP para categorías: {e}")
    except Exception as e:
        print(Fore.RED + f"Error inesperado al obtener categorías: {e}")

    # Devuelve la lista (puede estar vacía si no se encontraron o hubo error)
    return categorias if categorias else ["Otras"] # Decide si retornar ["Otras"] o [] en caso de fallo/no encontrar

def obtener_sinonimos(palabra):
    """Obtiene sinónimos de una palabra desde synonyms.reverso.net."""
    print(Fore.CYAN + f"--- Intentando obtener sinónimos para '{palabra}' desde Reverso...")
    palabra_codificada = quote(palabra.lower())
    url = f"https://synonyms.reverso.net/sinonimo/es/{palabra_codificada}"
    headers = {'User-Agent': USER_AGENT}
    lista_sinonimos = []

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        elementos_sinonimo = soup.select('li[id^="synonym-"] a, a.synonym') # Combinar selectores

        if not elementos_sinonimo:
            print(Fore.YELLOW + f"No se encontraron elementos de sinónimos para '{palabra}'.")
        else:
            for elemento in elementos_sinonimo:
                sinonimo = elemento.get_text(strip=True)
                if sinonimo:
                    lista_sinonimos.append(sinonimo)
            # Eliminar duplicados
            lista_sinonimos = sorted(list(dict.fromkeys(lista_sinonimos)))
            if lista_sinonimos:
                 print(Fore.GREEN + f"Sinónimos encontrados: {len(lista_sinonimos)}")
            else:
                 print(Fore.YELLOW + f"Se encontraron elementos, pero no se pudo extraer texto de sinónimos para '{palabra}'.")


    except requests.exceptions.Timeout:
        print(Fore.RED + f"Error: Timeout al obtener sinónimos para '{palabra}'.")
    except requests.exceptions.RequestException as e:
        # A menudo un 404 aquí significa que la palabra no estaba en Reverso
        if response.status_code == 404:
             print(Fore.YELLOW + f"La palabra '{palabra}' no fue encontrada en Reverso Synonyms.")
        else:
             print(Fore.RED + f"Error en la solicitud HTTP para sinónimos: {e}")
    except Exception as e:
        print(Fore.RED + f"Error inesperado al obtener sinónimos: {e}")

    return lista_sinonimos # Devuelve la lista (puede estar vacía)

# --- Funciones de Manejo de JSON ---

def cargar_datos_json(nombre_archivo):
    """Carga datos desde un archivo JSON, manejando errores."""
    if os.path.exists(nombre_archivo) and os.path.getsize(nombre_archivo) > 0:
        try:
            with open(nombre_archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, dict):
                print(Fore.YELLOW + f"Advertencia: El archivo '{nombre_archivo}' no contiene un diccionario JSON. Se iniciará uno nuevo.")
                return {}
            return datos
        except json.JSONDecodeError:
            print(Fore.RED + f"Error: El archivo '{nombre_archivo}' no tiene formato JSON válido. Se iniciará uno nuevo.")
            return {}
        except Exception as e:
            print(Fore.RED + f"Error inesperado al leer '{nombre_archivo}': {e}")
            return {} # Retorna diccionario vacío en caso de error de lectura
    else:
        if not os.path.exists(nombre_archivo):
             print(Fore.YELLOW + f"Archivo '{nombre_archivo}' no encontrado. Se creará uno nuevo.")
        # Si existe pero está vacío, no es necesario mensaje.
        return {}

def guardar_datos_json(nombre_archivo, datos):
    """Guarda un diccionario en un archivo JSON."""
    try:
        # Asegurarse de que el directorio exista
        directorio = os.path.dirname(nombre_archivo)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)
            print(Fore.GREEN + f"Directorio '{directorio}' creado.")

        with open(nombre_archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        # print(Fore.GREEN + f"Datos guardados correctamente en '{nombre_archivo}'.") # Opcional: menos verboso
    except Exception as e:
        print(Fore.RED + f"Error al escribir datos en '{nombre_archivo}': {e}")

# --- Flujo Principal ---
if __name__ == "__main__":
    producto_buscar = input("Ingrese el nombre del producto a buscar/clasificar: ").strip()

    if not producto_buscar:
        print(Fore.RED + "No ingresaste un nombre de producto.")
    else:
        # 1. Cargar datos existentes del JSON
        datos_guardados = cargar_datos_json(ARCHIVO_JSON)

        # 2. Verificar si el producto ya existe en el JSON (caché)
        if producto_buscar in datos_guardados:
            print(Back.GREEN + Fore.WHITE + f"\nProducto '{producto_buscar}' encontrado en el archivo JSON (caché).")
            datos_producto = datos_guardados[producto_buscar]
            categorias_final = datos_producto.get('categorias', ["No disponible"]) # Usar .get con default
            sinonimos_final = datos_producto.get('sinonimos', [])

            print(Style.BRIGHT + "\nCategorías (desde JSON):")
            if isinstance(categorias_final, list):
                 print(" -> ".join(categorias_final) if categorias_final else Fore.YELLOW + "Ninguna categoría guardada.")
            else: # Manejar el caso de "Otras" u otro string
                 print(categorias_final)

            print(Style.BRIGHT + "\nSinónimos (desde JSON):")
            if sinonimos_final:
                for s in sinonimos_final:
                    print(f"- {s}")
            else:
                print(Fore.YELLOW + "Ningún sinónimo guardado.")

        else:
            print(Back.YELLOW + Fore.BLACK + f"\nProducto '{producto_buscar}' no encontrado en JSON. Realizando scraping...")

            # 3. Realizar scraping si no está en caché
            categorias_scraped = obtener_categorias(producto_buscar)
            sinonimos_scraped = obtener_sinonimos(producto_buscar) # Pasar el mismo término de producto

            # 4. Preparar la nueva entrada para el JSON
            nueva_entrada = {
                "categorias": categorias_scraped,
                "sinonimos": sinonimos_scraped
            }

            # 5. Actualizar el diccionario en memoria y guardar en JSON
            datos_guardados[producto_buscar] = nueva_entrada
            guardar_datos_json(ARCHIVO_JSON, datos_guardados)

            print(Fore.GREEN + f"\nDatos para '{producto_buscar}' obtenidos y guardados en '{ARCHIVO_JSON}'.")

            # Mostrar los resultados recién obtenidos
            print(Style.BRIGHT + "\nCategorías (recién obtenidas):")
            if isinstance(categorias_scraped, list):
                 print(" -> ".join(categorias_scraped) if categorias_scraped else Fore.YELLOW + "No se obtuvieron categorías.")
            else:
                 print(categorias_scraped)

            print(Style.BRIGHT + "\nSinónimos (recién obtenidos):")
            if sinonimos_scraped:
                for s in sinonimos_scraped:
                    print(f"- {s}")
            else:
                print(Fore.YELLOW + "No se obtuvieron sinónimos.")