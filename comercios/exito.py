from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def scrapear(articulo, page):
    url = f"https://www.exito.com/s?q={articulo}"
    page.goto(url, timeout=20000) # le decimos a Playwright que carge la url
    page.wait_for_selector("article.productCard_productCard__M0677", timeout=10000) #que  espere el js

    soup = BeautifulSoup(page.content(), "html.parser")
    productos = soup.select("article.productCard_productCard__M0677")

    nombres, precios, puntuaciones, paginas, fechas, links = [], [], [], [], [],[]
    
    for producto in productos:
        nombre = producto.select_one("p.styles_name__qQJiK")
        if nombre:
            nombres.append(nombre.text.strip())
        else:
            nombres.append("No se encontro")

        precio = producto.select_one("p.priceSection_container-promotion_price-dashed__FJ7nI")
        if precio and precio.text.strip():  # Verifica que el precio existe y no está vacío
            precio_limpio = int(precio.text.replace('$', '').replace('.', '').replace(',', '').strip())
            precio_formateado = f"${precio_limpio:,.0f}"  # Formato con separadores
        else:
            precio_formateado = "No disponible"

        precios.append(precio_formateado)

        puntuaciones.append("No disponible")
        paginas.append("Éxito")
        fechas.append(datetime.now().strftime("%d/%m/%Y"))
        
        link = producto.select_one("a[data-testid=product-link]")  # Selector actualizado
        if link and link.has_attr("href"):
            links.append("https://www.exito.com" + link["href"])   # Combina con dominio base
        else:
            links.append("No  disponible")

    return pd.DataFrame({"Nombre": nombres, "Precio": precios, "Puntuacion": puntuaciones, "Fecha": fechas, "Links":links,"Pagina": paginas})
