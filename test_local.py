import requests, time, subprocess, sys, os

print("[*] Starting local server...")
p = subprocess.Popen([sys.executable, "app.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)

try:
    print("[*] Testing /api/refresh (waiting 30s for login)...")
    r = requests.get("http://127.0.0.1:5000/api/refresh", timeout=35)
    print(f"[+] Response: {r.json()}")
finally:
    p.terminate()
    print("[*] Server stopped.")
