import requests
import time
import datetime
import os
from flask import Flask, request

app = Flask(__name__)

# CONFIGURACIÓN
API_KEY = os.getenv("API_KEY")  # Clave API de Mercado Público
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Webhook de N8N

@app.route("/run", methods=["GET"])
def run_script():
    # Fecha actual en formato requerido
    fecha_actual = datetime.datetime.now().strftime('%d%m%Y')
    print(f"📅 Obteniendo licitaciones publicadas el {fecha_actual}")

    url = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
    licitaciones = []
    pagina = 1
    MAX_REINTENTOS = 3
    codigos_vistos = set()
    detener = False

    while not detener:
        params = {
            "fecha": fecha_actual,
            "estado": "publicada",
            "pagina": pagina,
            "ticket": API_KEY
        }
        intentos = 0
        while intentos < MAX_REINTENTOS:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                lista = data.get("Listado", [])
                if not lista:
                    print("✅ No hay más licitaciones.")
                    detener = True
                    break

                nuevos = 0
                for lic in lista:
                    codigo = lic.get("CodigoExterno", "")
                    url_publica = lic.get("UrlPublica", "")
                    if codigo in codigos_vistos:
                        continue

                    codigos_vistos.add(codigo)
                    nuevos += 1
                    licitaciones.append({
                        "codigo": codigo,
                        "nombre": lic.get("Nombre", ""),
                        "fecha_cierre": lic.get("FechaCierre", ""),
                        "url_publica": url_publica,
                        "tiene_url": bool(url_publica),
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
            else:
                print(f"⚠️ Error {response.status_code}. Reintentando...")
                intentos += 1
                time.sleep(2)

    if licitaciones:
        headers = {"Content-Type": "application/json"}
        res = requests.post(WEBHOOK_URL, json={"licitaciones": licitaciones}, headers=headers)
        if res.status_code == 200:
            return "✅ Licitaciones enviadas correctamente"
        else:
            return f"❌ Error al enviar al webhook: {res.status_code}", 500
    else:
        return "⚠️ No se encontraron licitaciones para hoy."

if __name__ == "__main__":
    app.run(debug=True)
