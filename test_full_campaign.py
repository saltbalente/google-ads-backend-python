#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Test Completo de Campaña con Targeting
"""

import requests
import json
import time

BACKEND_URL = "https://google-ads-backend-mm4z.onrender.com"
CUSTOMER_ID = "7094116152"

print("=" * 70)
print("GIGA-INGENIEUR BLACK - TEST COMPLETO DE CAMPAÑA CON TARGETING")
print("=" * 70)

# PASO 1: Crear Budget
print("\n📦 PASO 1: Creando presupuesto...")
budget_payload = {
    "customerId": CUSTOMER_ID,
    "name": f"GIGA-TEST-Budget-{int(time.time())}",
    "amountMicros": "10000000000",  # 10,000 COP
    "isShared": False
}

try:
    resp = requests.post(f"{BACKEND_URL}/api/create-budget", json=budget_payload, timeout=60)
    print(f"   Status: {resp.status_code}")
    budget_data = resp.json()
    print(f"   Response: {json.dumps(budget_data, indent=2)}")
    
    if not budget_data.get('success'):
        print("❌ Error creando budget")
        exit(1)
    
    budget_resource = budget_data.get('resourceName')
    print(f"✅ Budget creado: {budget_resource}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# PASO 2: Crear Campaña con Targeting
print("\n🚀 PASO 2: Creando campaña con targeting completo...")
campaign_payload = {
    "customerId": CUSTOMER_ID,
    "name": f"GIGA-TEST-Campaña-USA-ES-EN-{int(time.time())}",
    "budgetResourceName": budget_resource,
    "status": "PAUSED",
    "biddingStrategy": "MANUAL_CPC",  # Usar MANUAL_CPC para evitar problemas
    "geoTargets": ["2840"],  # USA
    "languages": ["1003", "1000"],  # Español, Inglés
    "excludeEuPoliticalAds": True
}

print(f"   Payload: {json.dumps(campaign_payload, indent=2)}")

try:
    resp = requests.post(f"{BACKEND_URL}/api/create-campaign", json=campaign_payload, timeout=60)
    print(f"\n   Status: {resp.status_code}")
    campaign_data = resp.json()
    print(f"   Response: {json.dumps(campaign_data, indent=2)}")
    
    if campaign_data.get('success'):
        print(f"\n✅ CAMPAÑA CREADA EXITOSAMENTE!")
        print(f"   Campaign ID: {campaign_data.get('campaignId')}")
        print(f"   Resource: {campaign_data.get('resourceName')}")
        print("\n🎯 VERIFICAR EN GOOGLE ADS:")
        print(f"   1. Ir a https://ads.google.com/")
        print(f"   2. Seleccionar cuenta {CUSTOMER_ID}")
        print(f"   3. Buscar campaña: {campaign_payload['name']}")
        print(f"   4. Verificar Ubicaciones: debe mostrar 'Estados Unidos'")
        print(f"   5. Verificar Idiomas: debe mostrar 'Español, Inglés'")
        print(f"   6. Verificar Política UE: debe mostrar 'No contiene'")
    else:
        print(f"\n❌ Error: {campaign_data.get('error')}")
        if 'errors' in campaign_data:
            for err in campaign_data['errors']:
                print(f"   - {err}")
        
except Exception as e:
    print(f"❌ Error: {e}")
