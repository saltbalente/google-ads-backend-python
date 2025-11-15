#!/usr/bin/env python3
"""
Script para verificar los criterios demográficos actuales en el ad group
"""

from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv
import os

load_dotenv()

def get_google_ads_client():
    return GoogleAdsClient.load_from_dict({
        "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": True
    })

customer_id = "5753767756"
ad_group_id = "166462715675"

client = get_google_ads_client()
google_ads_service = client.get_service("GoogleAdsService")

query = f"""
    SELECT
        ad_group_criterion.criterion_id,
        ad_group_criterion.type,
        ad_group_criterion.negative,
        ad_group_criterion.gender.type,
        ad_group_criterion.age_range.type,
        ad_group_criterion.income_range.type
    FROM ad_group_criterion
    WHERE ad_group_criterion.ad_group = 'customers/{customer_id}/adGroups/{ad_group_id}'
        AND ad_group_criterion.type IN ('GENDER', 'AGE_RANGE', 'INCOME_RANGE')
"""

print("\n" + "=" * 70)
print("📊 CRITERIOS DEMOGRÁFICOS ACTUALES EN EL AD GROUP")
print("=" * 70)

response = google_ads_service.search(customer_id=customer_id, query=query)

for row in response:
    criterion = row.ad_group_criterion
    criterion_type = criterion.type_.name
    is_negative = "❌ EXCLUIR (negative)" if criterion.negative else "✅ INCLUIR (positive)"
    
    if criterion_type == "GENDER":
        value = criterion.gender.type_.name
    elif criterion_type == "AGE_RANGE":
        value = criterion.age_range.type_.name
    elif criterion_type == "INCOME_RANGE":
        value = criterion.income_range.type_.name
    else:
        value = "Unknown"
    
    print(f"\n🎯 Criterion ID: {criterion.criterion_id}")
    print(f"   Tipo: {criterion_type}")
    print(f"   Valor: {value}")
    print(f"   Acción: {is_negative}")

print("\n" + "=" * 70 + "\n")
