from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from urllib.parse import urljoin

async def scrapear(articulo, page):
    await page.set_extra_http_headers({
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

    url = f"https://www.ktronix.com/search?text={articulo}"
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector("#js-hits", timeout=30000)
    except Exception as e:
        print(f"[ktronix] Timeout o error: {e}")
        return pd.DataFrame({
            "Nombre": [], "Precio": [], "Puntuacion": [],
            "Fecha": [], "Links": [], "Pagina": []
        })
    
    content = await page.content()
    soup = BeautifulSoup(content, "html.parser")
    productos = soup.select("li.ais-InfiniteHits-item")

    nombres, precios, puntuaciones, fechas, links, paginas = [], [], [], [], [], []
    base_url = "https://www.ktronix.com" 
    for producto in productos:
        nombre = producto.select_one("h3.product__item__top__title.js-algolia-product-click.js-algolia-product-title")
        nombres.append(nombre.text.strip() if nombre else "No encontrado")

        precio_span = producto.select_one("span.price") # Selecciona el span con la clase 'price'
        precio_limpio = 0
        if precio_span:
            texto = precio_span.text.strip() # Obtiene "$ 2.299.000"
            try:
                # Quita '$', '.' y posible espacio en blanco antes de convertir
                precio_limpio = int(texto.replace('$', '').replace('.', '').strip())
            except ValueError:
                precio_limpio = 0 # Maneja casos donde la conversión falle
        precios.append(f"${precio_limpio:,.0f}")
    
        puntuacion_span = producto.select_one("span.averageNumber")
        # Obtener el contenido de texto del span
        puntuaciones.append(puntuacion_span.text.strip() if puntuacion_span else "No disponible")

        link_element = producto.select_one("a.product__item__top__link")
        link_url = "No disponible" # Valor por defecto
        if link_element and link_element.has_attr("href"):
            relative_href = link_element["href"]
            # 3. Usa urljoin para construir la URL completa
            link_url = urljoin(base_url, relative_href)
        links.append(link_url)

        paginas.append("Ktronix")
        fechas.append(datetime.now().strftime("%d/%m/%Y"))

    return pd.DataFrame({
        "Nombre": nombres,
        "Precio": precios,
        "Puntuacion": puntuaciones,
        "Fecha": fechas,
        "Links": links,
        "Pagina": paginas
    })
