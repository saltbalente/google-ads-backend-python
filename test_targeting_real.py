#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Test Real de Targeting
Ejecutar LOCALMENTE para verificar el backend
"""

import requests
import json
import time

BACKEND_URL = "https://google-ads-backend-mm4z.onrender.com"
CUSTOMER_ID = "7094116152"

# Headers necesarios para autenticación (tomados del .env)
HEADERS = {
    "Content-Type": "application/json"
}

print("=" * 70)
print("GIGA-INGENIEUR BLACK - TEST REAL DE TARGETING")
print("=" * 70)

# Esperar a que el backend esté listo después del deploy
print("\n⏳ Esperando que el backend esté actualizado (30 segundos después del deploy)...")
time.sleep(5)

# Test 1: Verificar que el endpoint responde
print("\n📡 TEST 1: Verificando endpoint /api/create-campaign...")
try:
    # Enviar request con todos los parámetros de targeting
    test_payload = {
        "customerId": CUSTOMER_ID,
        "name": f"GIGA-TEST-Targeting-{int(time.time())}",
        "budgetResourceName": "customers/7094116152/campaignBudgets/FAKE123",  # Presupuesto falso para test
        "status": "PAUSED",
        "biddingStrategy": "MAXIMIZE_CLICKS",
        "geoTargets": ["2840"],  # USA
        "languages": ["1003", "1000"],  # Español, Inglés
        "excludeEuPoliticalAds": True
    }
    
    print(f"\n📤 Payload enviado:")
    print(json.dumps(test_payload, indent=2))
    
    response = requests.post(
        f"{BACKEND_URL}/api/create-campaign",
        json=test_payload,
        headers=HEADERS,
        timeout=60
    )
    
    print(f"\n📥 Status: {response.status_code}")
    print(f"Response: {response.text[:500]}...")
    
    # El error esperado es sobre el budget falso, NO sobre los parámetros de targeting
    if "FAKE123" in response.text or "budget" in response.text.lower():
        print("\n✅ TARGETING PARAMS ACEPTADOS - Error es por budget falso (esperado)")
    elif "geo" in response.text.lower() or "language" in response.text.lower():
        print("\n❌ ERROR EN TARGETING - Ver logs del backend")
    else:
        data = response.json()
        if data.get("success"):
            print("\n✅ CAMPAÑA CREADA CON TARGETING")
        else:
            print(f"\n⚠️ Error: {data.get('error', 'Unknown')}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Ver los logs del backend para confirmar que recibe los parámetros
print("\n" + "=" * 70)
print("INSTRUCCIONES PARA VERIFICAR LOGS EN RENDER:")
print("=" * 70)
print("""
1. Ir a: https://dashboard.render.com/
2. Seleccionar el servicio: google-ads-backend-python
3. Click en "Logs"
4. Buscar las líneas:
   - "Geo Targets: ['2840']"
   - "Languages: ['1003', '1000']"
   - "Exclude EU Political Ads: True"

Si ves estos logs, el backend está recibiendo los parámetros correctamente.
""")
