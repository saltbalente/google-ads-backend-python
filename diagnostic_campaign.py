#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Diagnóstico Post-Creación de Campaña
"""

import os
from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv

load_dotenv()

CUSTOMER_ID = "7094116152"
CAMPAIGN_ID = "23344433903"  # La campaña que acabamos de crear

print("=" * 70)
print("DIAGNÓSTICO POST-CREACIÓN DE CAMPAÑA")
print("=" * 70)

# Build client
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

# 1. Consultar configuración de la campaña
print("\n📊 1. CONFIGURACIÓN DE CAMPAÑA:")
query = f"""
    SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.bidding_strategy_type,
        campaign.contains_eu_political_advertising,
        campaign.manual_cpc.enhanced_cpc_enabled,
        campaign.network_settings.target_google_search,
        campaign.network_settings.target_search_network,
        campaign.network_settings.target_content_network
    FROM campaign
    WHERE campaign.id = {CAMPAIGN_ID}
"""

response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
for row in response:
    c = row.campaign
    print(f"   ID: {c.id}")
    print(f"   Nombre: {c.name}")
    print(f"   Estado: {c.status.name}")
    print(f"   Estrategia de puja: {c.bidding_strategy_type.name}")
    print(f"   EU Political Ads: {c.contains_eu_political_advertising.name}")
    print(f"   Enhanced CPC: {c.manual_cpc.enhanced_cpc_enabled}")
    print(f"   Target Google Search: {c.network_settings.target_google_search}")
    print(f"   Target Search Network: {c.network_settings.target_search_network}")
    print(f"   Target Content Network: {c.network_settings.target_content_network}")

# 2. Consultar criterios de ubicación
print("\n📍 2. GEO TARGETING (Ubicaciones):")
query = f"""
    SELECT
        campaign_criterion.location.geo_target_constant,
        campaign_criterion.negative
    FROM campaign_criterion
    WHERE campaign.id = {CAMPAIGN_ID}
        AND campaign_criterion.type = 'LOCATION'
"""

response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
locations_found = False
for row in response:
    locations_found = True
    cc = row.campaign_criterion
    neg = "EXCLUIDA" if cc.negative else "INCLUIDA"
    print(f"   {cc.location.geo_target_constant} - {neg}")

if not locations_found:
    print("   ❌ NO HAY UBICACIONES CONFIGURADAS")

# 3. Consultar criterios de idioma
print("\n🌐 3. LANGUAGE TARGETING (Idiomas):")
query = f"""
    SELECT
        campaign_criterion.language.language_constant
    FROM campaign_criterion
    WHERE campaign.id = {CAMPAIGN_ID}
        AND campaign_criterion.type = 'LANGUAGE'
"""

response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
languages_found = False
for row in response:
    languages_found = True
    print(f"   {row.campaign_criterion.language.language_constant}")

if not languages_found:
    print("   ❌ NO HAY IDIOMAS CONFIGURADOS")

# 4. Consultar criterios de dispositivo
print("\n📱 4. DEVICE TARGETING (Dispositivos):")
query = f"""
    SELECT
        campaign_criterion.device.type,
        campaign_criterion.bid_modifier
    FROM campaign_criterion
    WHERE campaign.id = {CAMPAIGN_ID}
        AND campaign_criterion.type = 'DEVICE'
"""

response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
devices_found = False
for row in response:
    devices_found = True
    cc = row.campaign_criterion
    print(f"   Dispositivo: {cc.device.type.name}, Bid Modifier: {cc.bid_modifier}")

if not devices_found:
    print("   ⚠️ NO HAY CRITERIOS DE DISPOSITIVO (= todos los dispositivos activos)")

print("\n" + "=" * 70)
print("ANÁLISIS RED-X:")
print("=" * 70)
