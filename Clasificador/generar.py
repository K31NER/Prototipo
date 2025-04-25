import os
import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import quote # Necesario para codificar el producto en la URL
from colorama import init, Fore, Back, Style # Para salida con colores

# --- Configuración Inicial ---
init(autoreset=True) # Inicializa colorama para colores en la terminal

# --- Constantes ---
DIRECTORIO_DATOS = "/" # Carpeta donde se guarda el JSON
ARCHIVO_CACHE_CATEGORIAS = os.path.join("categorias.json")
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
TIMEOUT_REQUEST = 15 # Tiempo máximo de espera para las solicitudes web (segundos)

# --- Funciones de Manejo del Caché JSON ---

def cargar_cache_json(ruta_archivo):
    """
    Carga los datos desde el archivo JSON de caché de forma segura.
    Devuelve un diccionario vacío si hay problemas.
    """
    if os.path.exists(ruta_archivo) and os.path.getsize(ruta_archivo) > 0:
        try:
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
            # Asegurarse de que lo cargado sea un diccionario
            if not isinstance(datos, dict):
                print(Fore.YELLOW + f"Advertencia: Caché '{ruta_archivo}' corrupto (no es diccionario). Se ignora.")
                return {}
            return datos
        except json.JSONDecodeError:
            print(Fore.RED + f"Error: Caché '{ruta_archivo}' corrupto (JSON inválido). Se ignora.")
            return {}
        except Exception as e:
            print(Fore.RED + f"Error inesperado al leer caché '{ruta_archivo}': {e}")
            return {}
    else:
        # Es normal si no existe o está vacío la primera vez
        return {}

def guardar_cache_json(ruta_archivo, datos_a_guardar):
    """
    Guarda el diccionario de datos (completo) en el archivo JSON de caché.
    Las claves (nombres de producto) ya deben estar en minúsculas.
    """
    try:
        # Asegurar que el directorio exista
        directorio = os.path.dirname(ruta_archivo)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)
            print(Fore.GREEN + f"Directorio '{directorio}' creado.")

        # Escribir el archivo completo
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            # Guardar con formato legible
            json.dump(datos_a_guardar, f, indent=4, ensure_ascii=False)
        # print(Fore.GREEN + f"Caché guardado en '{ruta_archivo}'.") 
    except Exception as e:
        print(Fore.RED + f"Error crítico al escribir caché '{ruta_archivo}': {e}")


# --- Función de Scraping de Categorías ---

def obtener_categorias_mercadolibre(producto_a_buscar):
    print(Fore.CYAN + f"--- Buscando categorías para '{producto_a_buscar}' en Mercado Libre...")
    # Codificamos el término para usarlo en la URL
    termino_codificado = quote(producto_a_buscar)
    url_pagina = f'https://listado.mercadolibre.com.co/{termino_codificado}'
    headers = {'User-Agent': USER_AGENT}
    categorias_encontradas = []

    try:
        response = requests.get(url_pagina, headers=headers, timeout=TIMEOUT_REQUEST)
        response.raise_for_status() # Verifica errores HTTP (4xx, 5xx)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Selector CSS para los nombres de categoría en el breadcrumb
        selector_categorias = 'ol.andes-breadcrumb li.andes-breadcrumb__item span[itemprop="name"]'
        elementos_categoria = soup.select(selector_categorias)

        if not elementos_categoria:
            print(Fore.YELLOW + f"  - No se encontraron elementos de categoría para '{producto_a_buscar}'. Asignando 'Otras'.")
            return ["Otras"]
        else:
            for elemento in elementos_categoria:
                nombre_categoria = elemento.get_text(strip=True)
                if nombre_categoria:
                    categorias_encontradas.append(nombre_categoria)

            if categorias_encontradas:
                 print(Fore.GREEN + "  - Categorías encontradas:", Style.BRIGHT + " -> ".join(categorias_encontradas))
                 return categorias_encontradas # Devolver la lista encontrada
            else:
                 print(Fore.YELLOW + f"  - Se encontraron elementos, pero no se pudo extraer texto. Asignando 'Otras'.")
                 return ["Otras"]

    except requests.exceptions.Timeout:
        print(Fore.RED + f"  - Error: Timeout al obtener categorías para '{producto_a_buscar}'.")
        return ["Otras"] # Valor por defecto en caso de error
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"  - Error en solicitud HTTP para categorías: {e}")
        return ["Otras"]
    except Exception as e:
        print(Fore.RED + f"  - Error inesperado al obtener categorías: {e}")
        return ["Otras"]

# --- Flujo Principal de Ejecución ---
if __name__ == "__main__":
    # 1. Solicitar el producto al usuario
    producto_input = input("Ingrese el nombre del producto a clasificar: ").strip()

    if not producto_input:
        print(Fore.RED + "Operación cancelada: No ingresaste un nombre de producto.")
    else:
        # Convertir a minúsculas para usar como clave y para la búsqueda en caché
        producto_clave = producto_input.lower()
        print("\n" + "="*50) # Separador visual

        # 2. Cargar datos del caché JSON
        print(f"{Style.BRIGHT}1. Cargando caché de categorías ({ARCHIVO_CACHE_CATEGORIAS})...{Style.RESET_ALL}")
        datos_cacheados = cargar_cache_json(ARCHIVO_CACHE_CATEGORIAS)
        print(f"   - {len(datos_cacheados)} productos en caché.")

        # 3. Verificar si el producto (en minúsculas) ya existe en el caché
        print(f"\n{Style.BRIGHT}2. Verificando si '{producto_clave}' está en caché...{Style.RESET_ALL}")
        if producto_clave in datos_cacheados:
            # --- Cache Hit ---
            print(Back.GREEN + Fore.WHITE + f">> ¡Encontrado en caché! <<")
            categorias_finales = datos_cacheados[producto_clave] # Recuperar del caché
            print(f"   - Usando categorías guardadas para '{producto_clave}'.")

        else:
            # --- Cache Miss ---
            print(Back.YELLOW + Fore.BLACK + f">> No encontrado en caché. Realizando scraping... <<")
            print(f"\n{Style.BRIGHT}3. Obteniendo categorías de la web para '{producto_input}'...{Style.RESET_ALL}")

            # Llamar a la función de scraping
            categorias_finales = obtener_categorias_mercadolibre(producto_input) # Pasar input original para búsqueda

            # 4. Actualizar el diccionario en memoria y guardar en JSON
            print(f"\n{Style.BRIGHT}4. Actualizando y guardando caché...{Style.RESET_ALL}")
            # Añadir/sobrescribir la entrada usando la clave en minúsculas
            datos_cacheados[producto_clave] = categorias_finales
            guardar_cache_json(ARCHIVO_CACHE_CATEGORIAS, datos_cacheados)
            print(Fore.GREEN + f"   - Categorías para '{producto_clave}' guardadas en caché.")

        # 5. Mostrar los resultados finales (de caché o recién obtenidos)
        print(f"\n{Style.BRIGHT}--- Resultado para '{producto_clave}' ---{Style.RESET_ALL}")
        print(Style.BRIGHT + "Categorías:")

        # Asegurarse de mostrar correctamente incluso si es ["Otras"] o lista vacía
        if isinstance(categorias_finales, list) and categorias_finales:
            print(Fore.MAGENTA + " -> ".join(categorias_finales))
        elif isinstance(categorias_finales, list) and not categorias_finales: # Raro, pero por si acaso
             print(Fore.YELLOW + "(No se encontraron categorías)")
        else: # Probablemente el string "Otras" si vino del caché antiguo o fallo
             print(Fore.YELLOW + str(categorias_finales)) # Convertir a string por seguridad

        print("\n" + "="*50) # Separador final