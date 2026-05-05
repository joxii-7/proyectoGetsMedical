import os
import subprocess
import time
import requests   # 👈 IMPORTANTE (arriba)

print("🚀 Iniciando sistema...")

# Ruta al backend
backend_path = os.path.join(os.getcwd(), "backend")

# 1. Iniciar Django
subprocess.Popen(
    ["cmd", "/k", "python manage.py runserver"],
    cwd=backend_path
)

# 2. ESPERAR A QUE DJANGO ESTÉ LISTO 👇 (AQUÍ VA TU CÓDIGO)
print("⏳ Esperando a Django...")

for _ in range(20):
    try:
        requests.get("http://127.0.0.1:8000")
        print("✅ Django listo")
        break
    except:
        time.sleep(1)

# 3. Recién aquí lanzar ngrok
subprocess.Popen(["cmd", "/k", "ngrok http 8000"])

print("\n🌐 ngrok iniciado")
input("Presiona ENTER para cerrar...")