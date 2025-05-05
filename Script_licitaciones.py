import requests
import time
import datetime
import os
from flask import Flask, request

# Flask App para Render
app = Flask(__name__)

# Configuración sensible desde entorno
API_KEY = os.getenv("API_KEY")  # ← Define en Render
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # ← Define en Render (con ?token=...)
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")  # ← Token de seguridad

@app.route("/run", methods=["GET"])
def run_script():
    token_recibido = request.args.get("token")
    
    # Validación de variables esenciales
    if not API_KEY or not WEBHOOK_URL or not ACCESS_TOKEN:
        return "❌ Configuración incompleta. Revisa las variables de entorno.", 500

    # Seguridad por token
    if token_recibido != ACCESS_TOKEN:
        return "❌ Token inválido", 403

    fecha_actual = datetime.datetime.now().strftime('%d%m%Y')
    print(f"📅 Obteniendo licitaciones publicadas el {fecha_actual}")

    url = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
    licitaciones = []
    pagina = 1
    MAX_REINTENTOS = 3
    MAX_LICITACIONES = 1000
    codigos_vistos = set()
    detener_por_bucle = False

    while not detener_por_bucle:
        intentos = 0
        params = {
            "fecha": fecha_actual,
            "estado": "publicada",
            "pagina": pagina,
            "ticket": API_KEY
        }

        while intentos < MAX_REINTENTOS:
            try:
                response = requests.get(url, params=params, timeout=20)
            except requests.exceptions.RequestException as e:
                print("❌ Error en la solicitud:", e)
                return "❌ Error en conexión a Mercado Público", 500

            if response.status_code == 200:
                data = response.json()
                lista = data.get("Listado", [])
                if not lista:
                    print("✅ Fin alcanzado: no hay más licitaciones.")
                    detener_por_bucle = True
                    break

                nuevos_en_esta_pagina = 0
                for lic in lista:
                    codigo = lic.get("CodigoExterno", "")
                    if codigo in codigos_vistos:
                        continue
                    codigos_vistos.add(codigo)
                    nuevos_en_esta_pagina += 1
                    licitaciones.append({
                        "codigo": codigo,
                        "nombre": lic.get("Nombre", ""),
                        "fecha_cierre": lic.get("FechaCierre", ""),
                        "ver_detalle": f"https://www.mercadopublico.cl/licitaciones/detalle/{codigo}",
                        "fecha_descarga": fecha_actual
                    })

                if nuevos_en_esta_pagina == 0:
                    print(f"🛑 Página {pagina} no contiene registros nuevos. Fin del bucle.")
                    detener_por_bucle = True
                    break

                print(f"✅ Página {pagina} cargada. Total acumulado: {len(licitaciones)}")

                # Control de límite para evitar sobrecarga
                if len(licitaciones) >= MAX_LICITACIONES:
                    print(f"🛑 Límite de {MAX_LICITACIONES} licitaciones alcanzado. Finalizando.")
                    detener_por_bucle = True
                    break

                pagina += 1
                time.sleep(0.3)
                break

            elif response.status_code == 500:
                print(f"⚠️ Error 500 en página {pagina}. Reintentando ({intentos+1}/{MAX_REINTENTOS})...")
                intentos += 1
                time.sleep(5)
            else:
                print(f"❌ Error inesperado - Código: {response.status_code}")
                detener_por_bucle = True
                break

        if intentos == MAX_REINTENTOS:
            print(f"❌ No se pudo recuperar la página {pagina} después de {MAX_REINTENTOS} intentos.")
            break

    # Enviar datos al webhook si hay resultados
    if licitaciones:
        headers = {"Content-Type": "application/json"}
        try:
            res = requests.post(WEBHOOK_URL, json={"licitaciones": licitaciones}, headers=headers, timeout=20)
            if res.status_code == 200:
                print("📤 Lote único enviado correctamente.")
                return "✅ Licitaciones enviadas correctamente"
            else:
                print("❌ Error al enviar al webhook:", res.status_code)
                return "❌ Fallo al enviar", 500
        except requests.exceptions.RequestException as e:
            print("❌ Error al conectar al webhook:", e)
            return "❌ Webhook inaccesible", 500
    else:
        print("⚠️ No se encontraron licitaciones.")
        return "⚠️ No hay licitaciones para hoy"

# Para ejecución local
if __name__ == "__main__":
    app.run(debug=True)
