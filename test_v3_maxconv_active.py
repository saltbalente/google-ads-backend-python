#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Test V3: MAX_CONVERSIONS + ACTIVE
USA, MOBILE only, Español, No EU Political Ads, ENABLED
"""

import requests
import json
import time

BACKEND_URL = "https://google-ads-backend-mm4z.onrender.com"
CUSTOMER_ID = "7094116152"

print("=" * 70)
print("GIGA-TEST V3: MAX CONVERSIONS + ACTIVA")
print("=" * 70)

# PASO 1: Crear Budget
print("\n📦 PASO 1: Creando presupuesto...")
budget_payload = {
    "customerId": CUSTOMER_ID,
    "name": f"Budget-MaxConv-V3-{int(time.time())}",
    "amountMicros": "10000000000",  # $10,000 USD
    "isShared": False
}

resp = requests.post(f"{BACKEND_URL}/api/create-budget", json=budget_payload, timeout=60)
budget_data = resp.json()
if not budget_data.get('success'):
    print(f"❌ Error creando budget: {budget_data}")
    exit(1)

budget_resource = budget_data.get('resourceName')
print(f"✅ Budget: {budget_resource}")

# PASO 2: Crear Campaña
print("\n🚀 PASO 2: Creando campaña con MAX_CONVERSIONS + ENABLED...")
campaign_payload = {
    "customerId": CUSTOMER_ID,
    "name": f"GIGA-V3-MaxConv-USA-ES-Mobile-ACTIVA-{int(time.time())}",
    "budgetResourceName": budget_resource,
    "status": "ENABLED",  # ⚡ ACTIVA, no pausada
    "biddingStrategy": "MAXIMIZE_CONVERSIONS",  # Max Conversiones
    "geoTargets": ["2840"],  # USA
    "languages": ["1003"],  # Solo Español
    "excludeEuPoliticalAds": True,  # NO contiene anuncios políticos UE
    "deviceTargets": ["MOBILE"]  # Solo móviles
}

print(f"\nPayload:")
print(json.dumps(campaign_payload, indent=2))

resp = requests.post(f"{BACKEND_URL}/api/create-campaign", json=campaign_payload, timeout=120)
print(f"\nStatus: {resp.status_code}")
campaign_data = resp.json()
print(f"\nResponse: {json.dumps(campaign_data, indent=2)}")

if campaign_data.get('success'):
    campaign_id = campaign_data.get('campaignId')
    print(f"\n" + "=" * 70)
    print(f"✅ CAMPAÑA CREADA EXITOSAMENTE")
    print(f"=" * 70)
    print(f"\n📋 DETALLES:")
    print(f"   Campaign ID: {campaign_id}")
    print(f"   Nombre: {campaign_payload['name']}")
    print(f"\n📊 CONFIGURACIÓN ESPERADA:")
    print(f"   ✅ Estado: ENABLED (Activa)")
    print(f"   ✅ Bidding: MAXIMIZE_CONVERSIONS")
    print(f"   ✅ Ubicación: Estados Unidos")
    print(f"   ✅ Idioma: Español")
    print(f"   ✅ EU Political Ads: NO contiene")
    print(f"   ✅ Dispositivos: Solo MOBILE")
    print(f"\n🔗 Verificar en Google Ads:")
    print(f"   https://ads.google.com/aw/campaigns?campaignId={campaign_id}")
else:
    print(f"\n❌ Error: {campaign_data.get('error')}")
    if 'errors' in campaign_data:
        for err in campaign_data['errors']:
            print(f"   - {err}")
