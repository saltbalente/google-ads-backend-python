#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Diagnóstico V3: Via API HTTP
"""

import requests
import json

BACKEND_URL = "https://google-ads-backend-mm4z.onrender.com"
CUSTOMER_ID = "7094116152"
CAMPAIGN_ID = "23339412459"

print("=" * 70)
print("DIAGNÓSTICO V3: CRITERIOS DE CAMPAÑA VIA API")
print("=" * 70)

# Obtener información de campaña y criterios
# Usar endpoint existente o hacer query directa

# Vamos a usar el endpoint de análisis de campaña si existe
# O crear una query manual

# Query GAQL para criterios
query = f"""
    SELECT
        campaign_criterion.criterion_id,
        campaign_criterion.type,
        campaign_criterion.device.type,
        campaign_criterion.bid_modifier,
        campaign_criterion.negative
    FROM campaign_criterion
    WHERE campaign.id = {CAMPAIGN_ID}
"""

payload = {
    "customerId": CUSTOMER_ID,
    "query": query
}

print(f"\nQuery: {query}")
print("\nEnviando a /api/googleads/query...")

try:
    resp = requests.post(
        f"{BACKEND_URL}/api/googleads/query",
        json=payload,
        timeout=60
    )
    print(f"\nStatus: {resp.status_code}")
    data = resp.json()
    print(f"\nResponse: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"\n❌ Error: {e}")

# Alternativa: probar endpoint de targeting
print("\n" + "=" * 70)
print("ALTERNATIVA: Obtener targeting directo")
print("=" * 70)

try:
    resp = requests.get(
        f"{BACKEND_URL}/api/campaign/{CUSTOMER_ID}/{CAMPAIGN_ID}/targeting",
        timeout=60
    )
    print(f"\nStatus: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nResponse: {json.dumps(data, indent=2)}")
    else:
        print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"\n❌ Error: {e}")
