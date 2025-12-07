#!/usr/bin/env python3
"""
Script para investigar la estructura de MaximizeConversions
"""

from google.ads.googleads.client import GoogleAdsClient
import os
from dotenv import load_dotenv

load_dotenv()

client = GoogleAdsClient.load_from_dict({
    "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
    "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID"),
    "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
    "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
    "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
    "use_proto_plus": True
})

campaign_operation = client.get_type("CampaignOperation")
campaign = campaign_operation.create

print("🔍 Investigando MaximizeConversions...")
print(f"\nTipo de maximize_conversions: {type(campaign.maximize_conversions)}")
print(f"\nDir de maximize_conversions:")
for attr in dir(campaign.maximize_conversions):
    if not attr.startswith('_'):
        print(f"  - {attr}")

print("\n\n🔍 Intentando diferentes enfoques:")

# Enfoque 1: Simplemente acceder al campo (esto debería marcarlo como presente)
print("\n1. Acceder al campo:")
_ = campaign.maximize_conversions
print("   ✓ Campo accedido")

# Enfoque 2: Verificar si tiene target_cpa_micros
print("\n2. Verificar atributos:")
if hasattr(campaign.maximize_conversions, 'target_cpa_micros'):
    print(f"   ✓ Tiene target_cpa_micros")
    print(f"   Valor por defecto: {campaign.maximize_conversions.target_cpa_micros}")
