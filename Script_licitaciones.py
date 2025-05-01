from flask import Flask, jsonify
import datetime
import requests
import os

app = Flask(__name__)

@app.route('/run', methods=['GET'])
def run_script():
    API_KEY = os.getenv("API_KEY")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")

    fecha_actual = datetime.datetime.now().strftime('%d%m%Y')
    url = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
    licitaciones = []
    pagina = 1
    codigos_vistos = set()
    detener = False

    while not detener:
        params = {
            "fecha": fecha_actual,
            "estado": "publicada",
            "pagina": pagina,
            "ticket": API_KEY
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            break
        data = response.json()
        lista = data.get("Listado", [])
        if not lista:
            break

        nuevos = 0
        for lic in lista:
            codigo = lic.get("CodigoExterno", "")
            if codigo in codigos_vistos:
                continue
            codigos_vistos.add(codigo)
            nuevos += 1
            licitaciones.append({
                "codigo": codigo,
                "nombre": lic.get("Nombre", ""),
                "fecha_cierre": lic.get("FechaCierre", ""),
                "ver_detalle": f"https://www.mercadopublico.cl/licitaciones/detalle/{codigo}",
                "fecha_descarga": fecha_actual
            })

        if nuevos == 0:
            break
        pagina += 1

    headers = {"Content-Type": "application/json"}
    res = requests.post(WEBHOOK_URL, json={"licitaciones": licitaciones}, headers=headers)
    return jsonify({"status": "success", "enviadas": len(licitaciones)}), 200
