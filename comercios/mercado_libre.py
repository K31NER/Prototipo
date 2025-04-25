from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def scrapear(articulo, page):  # Ahora usa 'page' de Playwright
    nombres, precios, puntuaciones, paginas, fechas, links = [], [], [], [], [], []
    url = f"https://listado.mercadolibre.com.co/{articulo}"

    try:
        # Cargar la página con Playwright
        page.goto(url, timeout=30000)
        page.wait_for_selector("li.ui-search-layout__item", timeout=30000)  # Esperar a los productos
        
        soup = BeautifulSoup(page.content(), "html.parser")
        productos = soup.find_all("li", class_="ui-search-layout__item")

        for producto in productos:
            try:
                # Nombre
                nombre_element = producto.find("h3", class_="poly-component__title-wrapper")
                nombres.append(nombre_element.text.strip() if nombre_element else "No encontrado")

                # Precio
                precio_element = producto.find("span", class_="andes-money-amount andes-money-amount--cents-superscript")
                if precio_element:
                    precio_texto = precio_element.text.replace("$", "").replace(".", "").strip()
                    precio_formateado = f"${int(precio_texto):,}" 
                else:
                    precio_formateado = "No disponible"
                precios.append(precio_formateado)

                # Puntuación (puede no existir)
                puntuacion_element = producto.find("span", class_="poly-reviews__rating")
                puntuaciones.append(puntuacion_element.text.strip() if puntuacion_element else "No disponible")

                # Links
                link_element = producto.find("a", class_="poly-component__title")
                links.append(link_element["href"] if link_element else "No disponible")

                paginas.append("Mercado Libre")
                fechas.append(datetime.now().strftime("%d/%m/%Y"))

            except Exception as e:
                print(f"Error procesando producto: {e}")

    except Exception as e:
        print(f"Error en Mercado Libre: {e}")

    return pd.DataFrame({
        "Nombre": nombres,
        "Precio": precios,
        "Puntuacion": puntuaciones,
        "Fecha": fechas,
        "Links": links,
        "Pagina": paginas
    })