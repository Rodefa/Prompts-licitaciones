import requests
import time
import datetime
import os
from flask import Flask, request
import pytz

app = Flask(__name__)

# CONFIGURACIÓN
API_KEY = os.getenv("API_KEY")  # Clave API de Mercado Público
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Webhook de N8N

# Validación de configuración
if not API_KEY or not WEBHOOK_URL:
    raise ValueError("🚫 Faltan variables de entorno: API_KEY o WEBHOOK_URL")

# Función para obtener licitaciones
def obtener_licitaciones(fecha_actual):
    url = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
    licitaciones = []
    pagina = 1
    codigos_vistos = set()
    detener = False
    MAX_REINTENTOS = 3

    while not detener:
        params = {
            "fecha": fecha_actual,
            "estado": "publicada",
            "pagina": pagina,
            "ticket": API_KEY
        }
        intentos = 0
        while intentos < MAX_REINTENTOS:
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                lista = data.get("Listado", [])

                if not lista:
                    print("✅ No hay más licitaciones.")
                    detener = True
                    break

                nuevos = 0
                for lic in lista:
                    codigo = lic.get("CodigoExterno", "")
                    if codigo in codigos_vistos:
                        continue
                    codigos_vistos.add(codigo)
                    nuevos += 1

                    url_publica = f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?CodigoExterno={codigo}"

                    licitaciones.append({
                        "codigo": codigo,
                        "nombre": lic.get("Nombre", ""),
                        "fecha_cierre": lic.get("FechaCierre", ""),
                        "url_publica": url_publica,
                        "fecha_descarga": fecha_actual
                    })

                if nuevos == 0:
                    print("🛑 Fin del bucle: sin nuevos registros.")
                    detener = True
                else:
                    print(f"✅ Página {pagina} cargada. Total: {len(licitaciones)}")
                    pagina += 1
                    time.sleep(0.3)
                break

            except requests.exceptions.HTTPError as err:
                print(f"🔥 Error HTTP en página {pagina}: {err}")
                intentos += 1
                time.sleep(2)

    return licitaciones

# Función para enviar al webhook de n8n
def enviar_a_webhook(licitaciones):
    headers = {"Content-Type": "application/json"}
    try:
        res = requests.post(WEBHOOK_URL, json={"licitaciones": licitaciones}, headers=headers)
        res.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al enviar al webhook: {e}")
        return False

@app.route("/run", methods=["GET"])
def run_script():
    tz = pytz.timezone('America/Santiago')
    fecha_actual = datetime.datetime.now(tz).strftime('%d%m%Y')

    print(f"📅 Obteniendo licitaciones publicadas el {fecha_actual}")

    licitaciones = obtener_licitaciones(fecha_actual)

    if licitaciones:
        exito = enviar_a_webhook(licitaciones)
        return "✅ Licitaciones enviadas correctamente" if exito else "❌ Error al enviar datos", 200 if exito else 500
    else:
        return "⚠️ No se encontraron licitaciones para hoy."

if __name__ == "__main__":
    app.run(debug=True)
