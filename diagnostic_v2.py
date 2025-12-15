#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Diagnóstico Campaña V2
"""

import os
from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv

load_dotenv()

CUSTOMER_ID = "7094116152"
CAMPAIGN_ID = "23339412459"  # La nueva campaña V2

print("=" * 70)
print(f"DIAGNÓSTICO CAMPAÑA: {CAMPAIGN_ID}")
print("=" * 70)

credentials = {
    "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
    "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
    "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
    "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
    "use_proto_plus": True,
    "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "8531174172")
}
client = GoogleAdsClient.load_from_dict(credentials)
ga_service = client.get_service("GoogleAdsService")

# 1. Configuración de campaña
print("\n📊 1. CONFIGURACIÓN DE CAMPAÑA:")
query = f"""
    SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.bidding_strategy_type,
        campaign.contains_eu_political_advertising
    FROM campaign
    WHERE campaign.id = {CAMPAIGN_ID}
"""

response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
for row in response:
    c = row.campaign
    print(f"   Nombre: {c.name}")
    print(f"   Estado: {c.status.name}")
    print(f"   Bidding: {c.bidding_strategy_type.name}")
    eu_status = c.contains_eu_political_advertising.name
    if "DOES_NOT" in eu_status:
        print(f"   EU Political: ✅ {eu_status}")
    else:
        print(f"   EU Political: ❌ {eu_status}")

# 2. Geo Targeting
print("\n📍 2. GEO TARGETING:")
query = f"""
    SELECT campaign_criterion.location.geo_target_constant
    FROM campaign_criterion
    WHERE campaign.id = {CAMPAIGN_ID}
        AND campaign_criterion.type = 'LOCATION'
"""
response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
found = False
for row in response:
    found = True
    geo = row.campaign_criterion.location.geo_target_constant
    if "2840" in geo:
        print(f"   ✅ {geo} (Estados Unidos)")
    else:
        print(f"   📍 {geo}")
if not found:
    print("   ❌ NO HAY UBICACIONES")

# 3. Language Targeting
print("\n🌐 3. IDIOMAS:")
query = f"""
    SELECT campaign_criterion.language.language_constant
    FROM campaign_criterion
    WHERE campaign.id = {CAMPAIGN_ID}
        AND campaign_criterion.type = 'LANGUAGE'
"""
response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
found = False
for row in response:
    found = True
    lang = row.campaign_criterion.language.language_constant
    if "1003" in lang:
        print(f"   ✅ {lang} (Español)")
    elif "1000" in lang:
        print(f"   ✅ {lang} (Inglés)")
    else:
        print(f"   🌐 {lang}")
if not found:
    print("   ❌ NO HAY IDIOMAS")

# 4. Device Targeting
print("\n📱 4. DISPOSITIVOS:")
query = f"""
    SELECT
        campaign_criterion.device.type,
        campaign_criterion.bid_modifier
    FROM campaign_criterion
    WHERE campaign.id = {CAMPAIGN_ID}
        AND campaign_criterion.type = 'DEVICE'
"""
response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
found = False
for row in response:
    found = True
    cc = row.campaign_criterion
    device = cc.device.type.name
    modifier = cc.bid_modifier
    if modifier == 0.0:
        print(f"   ⚠️ {device}: bid_modifier=0 (excluido/sin pujas)")
    elif modifier == -1.0:
        print(f"   ❌ {device}: EXCLUIDO (-100%)")
    else:
        print(f"   📱 {device}: bid_modifier={modifier}")
if not found:
    print("   ⚠️ No hay criterios de dispositivo configurados")

print("\n" + "=" * 70)
print("RESUMEN:")
print("=" * 70)
