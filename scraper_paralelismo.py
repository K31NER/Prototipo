from playwright.sync_api import sync_playwright
#from playwright_stealth import stealth_sync
import pandas as pd
import concurrent.futures  # Para paralelismo con procesos
import time
from datetime import datetime

# Importar funciones de scraping
from comercios.falabella import scrapear as scrapear_falabella
from comercios.alkosto import scrapear as scrapear_alkosto
from comercios.exito import scrapear as scrapear_exito
from comercios.jumbo import scrapear as scrapear_jumbo
from comercios.linio import scrapear as scrapear_linio
from comercios.mercado_libre import scrapear as scrapear_mercado_libre  

# Fecha actual en formato yyyy-mm-dd
fecha = datetime.now().strftime("%Y-%m-%d")

def scrapear_tienda(tienda, scrapear_func, articulo):
    """Ejecuta el scraping para una tienda específica en un proceso separado."""
    print(f"Scrapeando {tienda}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Bloquear imágenes para ir más rápido (Quitar si falla el scraping)
        page.route("**/*", lambda route, request: 
            route.abort() if request.resource_type in ["image"] else route.continue_()
        )
        #stealth_sync(page) # Aplicar técnicas de stealth
        
        df = scrapear_func(articulo, page)
        browser.close()  

    return df if not df.empty else None

def scrapear_todas_las_tiendas(articulo):
    dataframes = []
    tiempo_inicio = time.perf_counter()

    # Lista de funciones con parámetros
    tareas = [
        ("Falabella", scrapear_falabella, articulo),
        #("Alkosto", scrapear_alkosto, articulo),
        #("Éxito", scrapear_exito, articulo),
        #("Jumbo", scrapear_jumbo, articulo),
        ("Linio", scrapear_linio, articulo),
        #("Mercado Libre", scrapear_mercado_libre, articulo)
    ]

    # Ejecutar en paralelo usando ProcessPoolExecutor y submit()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futuros = {executor.submit(scrapear_tienda, *tarea): tarea[0] for tarea in tareas}

        for futuro in concurrent.futures.as_completed(futuros):
            tienda = futuros[futuro]
            try:
                df = futuro.result()
                if df is not None:
                    dataframes.append(df)
            except Exception as e:
                print(f"Error en {tienda}: {e}")

    tiempo_fin = time.perf_counter()
    print(f"Scraping completado en {tiempo_fin - tiempo_inicio:.2f} segundos.")
    
    # Esta tambien sirve para devolver csv
    data =  pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()
    
    # 🔁 Retornar lista de diccionarios (JSON-serializable)
    return data.to_dict(orient="records") if not data.empty else []

if __name__ == "__main__":
    articulo = input("Digite el nombre del artículo a buscar: ").strip()
    df_final = scrapear_todas_las_tiendas(articulo)

    if not df_final.empty:
        nombre_archivo = f"scraping_{articulo.replace(' ', '_')}_{fecha}.csv"
        ruta_completa = f"DATA/{nombre_archivo}"
        df_final.to_csv(ruta_completa, index=False, encoding="utf-8")
        print(f"Scraping finalizado. Datos guardados en {ruta_completa}")
    else:
        print("No se encontraron datos.")