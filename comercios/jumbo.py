from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def scrapear(articulo, page):
    url = f"https://www.tiendasjumbo.co/{articulo}"
    page.goto(url, timeout=20000) # le decimos a Playwright que carge la url
    page.wait_for_selector("div.tiendasjumboqaio-cmedia-integration-cencosud-0-x-galleryItem", timeout=10000) #que espere el js

    soup = BeautifulSoup(page.content(), "html.parser")
    productos = soup.select("div.tiendasjumboqaio-cmedia-integration-cencosud-0-x-galleryItem")

    nombres, precios, puntuaciones, paginas, fechas,links = [], [], [], [], [] ,[]
    
    for producto in productos:
        nombre = producto.select_one("span.vtex-product-summary-2-x-productBrand")
        if nombre:
            nombres.append(nombre.text.strip())
        else:
            nombres.append("No se encontro")
        precio = producto.select_one("div.tiendasjumboqaio-jumbo-minicart-2-x-price")
        if precio and precio.text.strip():  # Verifica que el precio existe y no está vacío
            precio_limpio = int(precio.text.replace('$', '').replace('.', '').replace(',', '').strip())
            precio_formateado = f"${precio_limpio:,.0f}"  # Formatea con separadores de miles
        else:
            precio_formateado = "No disponible"
        precios.append(precio_formateado)

        puntuaciones.append("No disponible")
        paginas.append("Jumbo")
        fechas.append(datetime.now().strftime("%d/%m/%Y"))
        
        link = producto.select_one("a.vtex-product-summary-2-x-clearLink")
        if link and link.has_attr("href"):  # Verifica que el enlace y el atributo href existan
            links.append("https://www.jumbocolombia.com/" + link["href"])
        else:
            links.append("No disponible")


    return pd.DataFrame({"Nombre": nombres, "Precio": precios, "Puntuacion": puntuaciones, "Fecha": fechas,"Links":links, "Pagina": paginas})
