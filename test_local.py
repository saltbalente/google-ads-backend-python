#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Test Local
"""

import requests
import json
import time

# Usar servidor LOCAL
BACKEND_URL = "http://127.0.0.1:10000"
CUSTOMER_ID = "7094116152"

print("=" * 70)
print("GIGA-INGENIEUR BLACK - TEST LOCAL")
print("=" * 70)

# PASO 1: Crear Budget
print("\n📦 PASO 1: Creando presupuesto...")
budget_payload = {
    "customerId": CUSTOMER_ID,
    "name": f"GIGA-LOCAL-Budget-{int(time.time())}",
    "amountMicros": "10000000000",
    "isShared": False
}

resp = requests.post(f"{BACKEND_URL}/api/create-budget", json=budget_payload, timeout=60)
print(f"Status: {resp.status_code}")
budget_data = resp.json()
print(f"Response: {json.dumps(budget_data, indent=2)}")

if not budget_data.get('success'):
    print(f"❌ Error: {budget_data}")
    exit(1)

budget_resource = budget_data.get('resourceName')
print(f"✅ Budget: {budget_resource}")

# PASO 2: Crear Campaña con TODOS los parámetros
print("\n🚀 PASO 2: Creando campaña con targeting completo...")
campaign_payload = {
    "customerId": CUSTOMER_ID,
    "name": f"GIGA-LOCAL-USA-ES-EN-MOBILE-{int(time.time())}",
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
else:
    print(f"\n❌ Error: {campaign_data.get('error')}")
    if 'errors' in campaign_data:
        for err in campaign_data['errors']:
            print(f"   - {err}")
