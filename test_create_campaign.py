#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Test de creación de campaña con targeting
"""

import requests
import json

# Configuración
BACKEND_URL = "https://google-ads-backend-mm4z.onrender.com"
CUSTOMER_ID = "7094116152"

# Headers - obtener tokens de la app
# Necesitamos el refresh token de la app

def test_create_budget():
    """Crear presupuesto de prueba"""
    url = f"{BACKEND_URL}/api/create-budget"
    
    payload = {
        "customerId": CUSTOMER_ID,
        "name": f"GIGA-TEST-Budget",
        "amountMicros": "10000000000",  # 10,000 COP
        "isShared": False
    }
    
    print(f"📤 Enviando a {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    
    print(f"📥 Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    return response.json() if response.status_code == 200 else None

def test_create_campaign_with_targeting():
    """Crear campaña con targeting completo"""
    url = f"{BACKEND_URL}/api/create-campaign"
    
    payload = {
        "customerId": CUSTOMER_ID,
        "name": "GIGA-TEST-Campaign-Targeting",
        "budgetResourceName": "customers/7094116152/campaignBudgets/123456789",  # Placeholder
        "status": "PAUSED",
        "biddingStrategy": "MAXIMIZE_CLICKS",
        "geoTargets": ["2840"],  # USA
        "languages": ["1003", "1000"],  # Español, Inglés
        "excludeEuPoliticalAds": True
    }
    
    print(f"\n📤 Enviando a {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    
    print(f"📥 Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    return response.json() if response.status_code == 200 else None

# Primero verificar que el servidor responde
print("=" * 60)
print("GIGA-INGENIEUR BLACK - TEST DE TARGETING")
print("=" * 60)

# Test health
try:
    health = requests.get(f"{BACKEND_URL}/health", timeout=10)
    print(f"✅ Backend activo: {health.text}")
except Exception as e:
    print(f"❌ Backend no responde: {e}")
    exit(1)

# Mostrar payload esperado
print("\n" + "=" * 60)
print("PAYLOAD QUE DEBE ENVIAR LA APP SWIFT:")
print("=" * 60)
print(json.dumps({
    "customerId": CUSTOMER_ID,
    "name": "Test Campaign",
    "budgetResourceName": "customers/xxx/campaignBudgets/yyy",
    "status": "PAUSED",
    "biddingStrategy": "MAXIMIZE_CLICKS",
    "geoTargets": ["2840"],
    "languages": ["1003", "1000"],
    "excludeEuPoliticalAds": True
}, indent=2))

print("\n" + "=" * 60)
print("RED-X ANALYSIS: Verificar qué envía la app Swift")
print("=" * 60)
print("""
Para diagnosticar, necesito ver los logs del backend cuando
la app Swift crea una campaña.

Los logs mostrarán:
- "Geo Targets: [...]" - debe tener IDs
- "Languages: [...]" - debe tener IDs
- "Exclude EU Political Ads: True/False"

Si estos están vacíos [], el problema está en SWIFT.
Si tienen valores pero no se aplican, el problema está en PYTHON.
""")
