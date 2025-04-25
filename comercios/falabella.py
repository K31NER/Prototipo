from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def scrapear(articulo, page):
    url = f"https://www.falabella.com.co/falabella-co/search?Ntt={articulo}"
    page.goto(url, timeout=30000) # le decimos a Playwright que carge la url
    page.wait_for_selector("div.jsx-2420634928.search-results--products", timeout=30000) #que espere el js

    soup = BeautifulSoup(page.content(), "html.parser")
    productos = soup.select("div.jsx-1068418086.search-results-4-grid.grid-pod")

    nombres, precios, puntuaciones, paginas, fechas,links = [], [], [], [], [],[]
    
    for producto in productos:
        nombre = producto.select_one("b.pod-subTitle")
        if nombres:
            nombres.append(nombre.text.strip())
        else:
            nombres.append("No se encontro")

        precio = producto.select_one("span.copy10.primary.medium")
        # Cámbiala por esto:
        if precio:
            # Elimina símbolos y espacios
            precio_limpio = precio.text.replace('$', '').replace('.', '').replace(',', '').strip()
            # Si hay un rango (ej: "349900 - 449900"), toma el primer valor
            if '-' in precio_limpio:
                primer_precio = precio_limpio.split('-')[0].strip()
                precio_numerico = int(primer_precio)  
                precio_formateado = f"${precio_numerico:,.0f}"
                precios.append(precio_formateado)
            else:
                precio_numerico = int(precio_limpio)  
                precio_formateado = f"${precio_numerico:,.0f}"
                precios.append(precio_formateado)
        else:
            precios.append("$0")  


        puntuacion = producto.select_one("div.ratings")
        puntuaciones.append(puntuacion.get('data-rating') if puntuacion else "No disponible")

        paginas.append("Falabella")
        fechas.append(datetime.now().strftime("%d/%m/%Y"))
        
        link = producto.select_one("a.pod-link")
        if link and link.has_attr("href"):  # Verifica que el enlace y el atributo href existan
            links.append(link["href"])
        else:
            links.append("No disponible")

    return pd.DataFrame({"Nombre": nombres, "Precio": precios, "Puntuacion": puntuaciones, "Fecha": fechas, "Links":links,"Pagina": paginas})
