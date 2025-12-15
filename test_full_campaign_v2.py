#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Test Completo V2 con Device Targeting
"""

import requests
import json
import time

BACKEND_URL = "https://google-ads-backend-mm4z.onrender.com"
CUSTOMER_ID = "7094116152"

print("=" * 70)
print("GIGA-INGENIEUR BLACK - TEST V2: EU + DEVICES + GEO + LANG")
print("=" * 70)

# Esperar deploy
print("\n⏳ Esperando que el backend se actualice...")
time.sleep(10)

# PASO 1: Crear Budget
print("\n📦 PASO 1: Creando presupuesto...")
budget_payload = {
    "customerId": CUSTOMER_ID,
    "name": f"GIGA-TEST-Budget-V2-{int(time.time())}",
    "amountMicros": "10000000000",
    "isShared": False
}

resp = requests.post(f"{BACKEND_URL}/api/create-budget", json=budget_payload, timeout=60)
budget_data = resp.json()
if not budget_data.get('success'):
    print(f"❌ Error: {budget_data}")
    exit(1)

budget_resource = budget_data.get('resourceName')
print(f"✅ Budget: {budget_resource}")

# PASO 2: Crear Campaña con TODOS los parámetros
print("\n🚀 PASO 2: Creando campaña con targeting completo...")
campaign_payload = {
    "customerId": CUSTOMER_ID,
    "name": f"GIGA-TEST-V2-USA-ES-EN-MOBILE-{int(time.time())}",
    "budgetResourceName": budget_resource,
    "status": "PAUSED",
    "biddingStrategy": "MANUAL_CPC",
    "geoTargets": ["2840"],  # USA
    "languages": ["1003", "1000"],  # Español, Inglés
    "excludeEuPoliticalAds": True,  # NO contiene anuncios políticos UE
    "deviceTargets": ["MOBILE"]  # Solo móviles
}

print(f"Payload: {json.dumps(campaign_payload, indent=2)}")

resp = requests.post(f"{BACKEND_URL}/api/create-campaign", json=campaign_payload, timeout=120)
print(f"\nStatus: {resp.status_code}")
campaign_data = resp.json()
print(f"Response: {json.dumps(campaign_data, indent=2)}")

if campaign_data.get('success'):
    campaign_id = campaign_data.get('campaignId')
    print(f"\n✅ CAMPAÑA CREADA: {campaign_id}")
    print(f"\n📋 VERIFICAR EN GOOGLE ADS:")
    print(f"   Campaña: {campaign_payload['name']}")
    print(f"   - Ubicación: Estados Unidos (2840)")
    print(f"   - Idiomas: Español + Inglés")
    print(f"   - EU Pol Ads: NO contiene")
    print(f"   - Dispositivos: Solo MOBILE (Desktop/Tablet excluidos)")
else:
    print(f"\n❌ Error: {campaign_data.get('error')}")
    if 'errors' in campaign_data:
        for err in campaign_data['errors']:
            print(f"   - {err}")
