import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime

# Importaciones locales
from comercios.falabella import scrapear as scrapear_falabella
from comercios.linio import scrapear as scrapear_linio
from comercios.mercado_libre import scrapear as scrapear_mercado_libre
from comercios.ktronix import scrapear as scrapear_ktronix

fecha = datetime.now().strftime("%Y-%m-%d")

# Diccionario de tiendas
TIENDAS = {
    #"Falabella": scrapear_falabella,
    #"Linio": scrapear_linio,
    "ktronix": scrapear_ktronix,
    #"Mercado Libre": scrapear_mercado_libre
}

async def scrapear_tienda(context, tienda, scrapear_func, articulo):
    print(f"Scrapeando {tienda}...")
    try:
        page = await context.new_page()
        df = await scrapear_func(articulo, page)
        await page.close()
        return df
    except Exception as e:
        print(f"Error en {tienda}: {e}")
        return None

async def scrapear_todas_las_tiendas(articulo):
    dataframes = []
    tiempo_inicio = asyncio.get_event_loop().time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def route_handler(route, request):
            if request.resource_type in ["image", "stylesheet", "font"]:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", route_handler)

        tareas = [
            scrapear_tienda(context, tienda, func, articulo)
            for tienda, func in TIENDAS.items()
        ]

        resultados = await asyncio.gather(*tareas)

        for df in resultados:
            if df is not None and not df.empty:
                dataframes.append(df)

        await browser.close()

    tiempo_fin = asyncio.get_event_loop().time()
    print(f"Scraping completado en {tiempo_fin - tiempo_inicio:.2f} segundos.")

    data = pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()
    return data.to_dict(orient="records") if not data.empty else []

if __name__ == "__main__":
    articulo = input("Digite el nombre del artículo a buscar: ").strip()
    resultados = asyncio.run(scrapear_todas_las_tiendas(articulo))

    if resultados:
        nombre_archivo = f"scraping_{articulo.replace(' ', '_')}_{fecha}.csv"
        ruta_completa = f"DATA/{nombre_archivo}"
        df = pd.DataFrame(resultados)
        df.to_csv(ruta_completa, index=False, encoding="utf-8")
        print(f"Scraping finalizado. Datos guardados en {ruta_completa}")
    else:
        print("No se encontraron datos.")