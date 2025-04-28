from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def scrapear(articulo, page):
    page.set_extra_http_headers({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CO,es;q=0.9",
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
    })
    
    url = f"https://linio.falabella.com.co/linio-co/search?Ntt={articulo}"
    try:
        page.goto(url, timeout=20000)
        page.wait_for_selector("div.search-results--products", timeout=10000)
    except TimeoutError:
        print(f"Error: Timeout al cargar {url}, omitiendo sitio…")
        # Devuelves un DataFrame vacío con las mismas columnas
        return pd.DataFrame({
            "Nombre": [], "Precio": [], "Puntuacion": [],
            "Fecha": [], "Links": [], "Pagina": []
        }) 

    soup = BeautifulSoup(page.content(), "html.parser")
    productos = soup.select("div.grid-pod")

    nombres, precios, puntuaciones, paginas, fechas, links = [], [], [], [], [], []
    
    for producto in productos:
        # Nombre
        nombre = producto.select_one("b.pod-subTitle")
        nombres.append(nombre.text.strip() if nombre else "No encontrado")

        # Precio (corrección clave)
        precio = producto.select_one("span.copy10.primary.medium")
        precio_limpio = 0  # Valor por defecto
        
        if precio:
            try:
                # Limpiar espacios no estándar y caracteres especiales
                texto_precio = precio.text.replace('\xa0', ' ').strip()
                
                # Manejar rangos de precios
                if '-' in texto_precio:
                    primer_precio = texto_precio.split('-')[0].strip()
                    precio_limpio = int(primer_precio.replace('$', '').replace('.', ''))
                else:
                    precio_limpio = int(texto_precio.replace('$', '').replace('.', ''))
                    
            except (ValueError, AttributeError):
                precio_limpio = 0

        precios.append(f"${precio_limpio:,.0f}")

        # Puntuación
        puntuacion = producto.select_one("div.ratings")
        puntuaciones.append(puntuacion.get('data-rating') if puntuacion else "No disponible")

        # Links
        link = producto.select_one("a.pod-link")
        links.append(link["href"] if link and link.has_attr("href") else "No disponible")

        # Metadata fija
        paginas.append("Linio")
        fechas.append(datetime.now().strftime("%d/%m/%Y"))

    return pd.DataFrame({
        "Nombre": nombres,
        "Precio": precios,
        "Puntuacion": puntuaciones,
        "Fecha": fechas,
        "Links": links,
        "Pagina": paginas
    })