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

    url = f"https://linio.falabella.com.co/linio-co/search?Ntt={articulo}"
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector("div.search-results--products", timeout=30000)
    except Exception as e:
        print(f"[Linio] Timeout o error: {e}")
        return pd.DataFrame({
            "Nombre": [], "Precio": [], "Puntuacion": [],
            "Fecha": [], "Links": [], "Pagina": []
        })

    content = await page.content()
    soup = BeautifulSoup(content, "html.parser")
    productos = soup.select("div.grid-pod")

    nombres, precios, puntuaciones, fechas, links, paginas = [], [], [], [], [], []

    for producto in productos:
        nombre = producto.select_one("b.pod-subTitle")
        nombres.append(nombre.text.strip() if nombre else "No encontrado")

        precio = producto.select_one("span.copy10.primary.medium")
        precio_limpio = 0
        if precio:
            texto = precio.text.replace('\xa0', ' ').strip()
            if '-' in texto:
                texto = texto.split('-')[0].strip()
            try:
                precio_limpio = int(texto.replace('$', '').replace('.', ''))
            except:
                precio_limpio = 0
        precios.append(f"${precio_limpio:,.0f}")

        puntuacion = producto.select_one("div.ratings")
        puntuaciones.append(puntuacion.get('data-rating') if puntuacion else "No disponible")

        link = producto.select_one("a.pod-link")
        links.append(link["href"] if link and link.has_attr("href") else "No disponible")

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
