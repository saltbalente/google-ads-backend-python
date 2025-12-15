#!/usr/bin/env python3
"""
GIGA-INGENIEUR BLACK - Diagnóstico V3: Device Criteria RAW
"""

from google.ads.googleads.client import GoogleAdsClient
import os

CUSTOMER_ID = "7094116152"
CAMPAIGN_ID = "23339412459"

os.chdir(os.path.dirname(os.path.abspath(__file__)))
client = GoogleAdsClient.load_from_storage("google-ads.yaml")
ga_service = client.get_service("GoogleAdsService")

print("=" * 70)
print("DIAGNÓSTICO V3: CRITERIOS DE DISPOSITIVO RAW")
print("=" * 70)

# Query para ver TODOS los criterios de campaña
query = f"""
    SELECT
        campaign.id,
        campaign.name,
        campaign_criterion.criterion_id,
        campaign_criterion.type,
        campaign_criterion.device.type,
        campaign_criterion.bid_modifier,
        campaign_criterion.negative
    FROM campaign_criterion
    WHERE campaign.id = {CAMPAIGN_ID}
"""

print(f"\n📋 Todos los criterios de campaña {CAMPAIGN_ID}:")
print("-" * 70)

response = ga_service.search(customer_id=CUSTOMER_ID, query=query)

for row in response:
    crit = row.campaign_criterion
    criterion_type = crit.type_.name if hasattr(crit.type_, 'name') else str(crit.type_)
    
    print(f"\n   Criterion ID: {crit.criterion_id}")
    print(f"   Type: {criterion_type}")
    print(f"   Negative: {crit.negative}")
    print(f"   Bid Modifier: {crit.bid_modifier}")
    
    if criterion_type == "DEVICE":
        device_type = crit.device.type_.name if hasattr(crit.device.type_, 'name') else str(crit.device.type_)
        print(f"   Device Type: {device_type}")

print("\n" + "=" * 70)
print("FIN DIAGNÓSTICO V3")
print("=" * 70)
