from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

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

    url = f"https://www.falabella.com.co/falabella-co/search?Ntt={articulo}"

    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector("div.jsx-2420634928.search-results--products", timeout=30000)
    except Exception as e:
        print(f"[Falabella] Timeout o error: {e}")
        return pd.DataFrame({
            "Nombre": [], "Precio": [], "Puntuacion": [],
            "Fecha": [], "Links": [], "Pagina": []
        })

    content = await page.content()
    soup = BeautifulSoup(content, "html.parser")
    productos = soup.select("div.jsx-1068418086.search-results-4-grid.grid-pod")

    nombres, precios, puntuaciones, fechas, links, paginas = [], [], [], [], [], []

    for producto in productos:
        nombre = producto.select_one("b.pod-subTitle")
        nombres.append(nombre.text.strip() if nombre else "No se encontró")

        precio = producto.select_one("span.copy10.primary.medium")
        if precio:
            texto = precio.text.replace('$', '').replace('.', '').replace(',', '').strip()
            if '-' in texto:
                texto = texto.split('-')[0].strip()
            try:
                precio_numerico = int(texto)
                precios.append(f"${precio_numerico:,.0f}")
            except:
                precios.append("$0")
        else:
            precios.append("$0")

        puntuacion_element = producto.find("span", class_="reviewCount")
        puntuaciones.append(puntuacion_element.get("data-rating") if puntuacion_element else "No disponible")

        link = producto.select_one("a.pod-link")
        links.append(link["href"] if link and link.has_attr("href") else "No disponible")

        paginas.append("Falabella")
        fechas.append(datetime.now().strftime("%d/%m/%Y"))

    return pd.DataFrame({
        "Nombre": nombres,
        "Precio": precios,
        "Puntuacion": puntuaciones,
        "Fecha": fechas,
        "Links": links,
        "Pagina": paginas
    })
