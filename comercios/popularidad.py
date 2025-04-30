import os
import time
import json
import pytz
from datetime import datetime
from pytrends.request import TrendReq

# Horarios autorizados para actualizar popularidad (hora local Colombia)
HORARIOS_VALIDOS = ["06:00", "13:00", "18:00", "21:00"]
RUTA_JSON = "comercios/popularidad_comercios.json"
ZONA_HORARIA_COLOMBIA = pytz.timezone('America/Bogota')

def obtener_ultima_franja():
    ahora = datetime.now(ZONA_HORARIA_COLOMBIA)
    hora_actual = ahora.time()
    franjas = [datetime.strptime(h, "%H:%M").time() for h in HORARIOS_VALIDOS]
    franjas_pasadas = [h for h in franjas if h <= hora_actual]

    if not franjas_pasadas:
        return HORARIOS_VALIDOS[-1], ahora.replace(day=ahora.day - 1).date()
    else:
        return max(franjas_pasadas).strftime("%H:%M"), ahora.date()

def registrar_actualizacion(franja, fecha, resultados):
    data = {
        "ultima_actualizacion": f"{fecha} {franja}",
        "status": "ok",
        "datos": resultados
    }
    with open(RUTA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def debe_actualizar_popularidad():
    franja_actual, fecha_actual = obtener_ultima_franja()
    timestamp_actual = f"{fecha_actual} {franja_actual}"

    if os.path.exists(RUTA_JSON):
        with open(RUTA_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            ultima_ejecucion = data.get("ultima_actualizacion")

        if ultima_ejecucion == timestamp_actual:
            return False
    return True

def obtener_popularidad():
    try:
        ahora = datetime.now(ZONA_HORARIA_COLOMBIA)
        timestamp_actual = ahora.strftime("%Y-%m-%d %H:%M:%S")
        franja_actual, fecha_actual = obtener_ultima_franja()

        if os.path.exists(RUTA_JSON) and not debe_actualizar_popularidad():
            print(f"⏰ No es necesario actualizar (última franja ya cubierta). Usando archivo: {timestamp_actual}")
            with open(RUTA_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("datos", [])

        print(f"⚡ Actualizando popularidad desde Google Trends: {timestamp_actual}")
        comercios = ["Mercado Libre", "Falabella", "Ktronix", "Jumbo", "Linio", "Exito"]
        pytrends = TrendReq(hl='es', tz=360, timeout=(10, 25))
        resultados = []

        for comercio in comercios:
            pytrends.build_payload([comercio], cat=0, timeframe='now 1-d', geo='CO', gprop='')
            data = pytrends.interest_over_time()

            if not data.empty:
                valor = data[comercio].dropna().replace(0, float('nan')).dropna()
                valor = valor.iloc[-1] if not valor.empty else 10
            else:
                valor = 10

            resultados.append({"comercio": comercio, "popularidad": valor})
            time.sleep(5)

        registrar_actualizacion(franja_actual, fecha_actual, resultados)
        print(f"✅ Popularidad actualizada y registrada en JSON: {RUTA_JSON}")
        return resultados

    except Exception as e:
        print(f"❌ Error al buscar popularidad: {e}")
        if os.path.exists(RUTA_JSON):
            print("♻️ Reciclando datos existentes debido al error.")
            with open(RUTA_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("datos", [])
        return []