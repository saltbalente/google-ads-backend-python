#!/usr/bin/env python3
"""
Probar el enfoque CORRECTO: usar FROM ad_group con segments.gender
"""
import os
from datetime import datetime, timedelta
from google.ads.googleads.client import GoogleAdsClient

def get_client():
    credentials = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "use_proto_plus": True,
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    }
    return GoogleAdsClient.load_from_dict(credentials)

customer_id = "5852810891"
ad_group_id = "175024723431"
days = 7

date_end = datetime.now().strftime('%Y-%m-%d')
date_start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

print(f"\n🧪 TEST: FROM ad_group WITH segments.gender")
print(f"Periodo: {date_start} a {date_end}\n")

client = get_client()
service = client.get_service("GoogleAdsService")

# Query correcto: FROM ad_group con segments
query = f"""
    SELECT
        segments.gender,
        metrics.conversions,
        metrics.clicks,
        metrics.impressions,
        metrics.cost_micros
    FROM ad_group
    WHERE ad_group.id = {ad_group_id}
        AND segments.date BETWEEN '{date_start}' AND '{date_end}'
"""

print("Query ejecutando...")
response = service.search(customer_id=customer_id, query=query)

print("\nResultados:")
total_rows = 0
for row in response:
    total_rows += 1
    gender = row.segments.gender
    print(f"\n  Gender: {gender.name} (value={gender.value})")
    print(f"    Conversiones: {row.metrics.conversions}")
    print(f"    Clicks: {row.metrics.clicks}")
    print(f"    Impresiones: {row.metrics.impressions}")
    print(f"    Costo: ${row.metrics.cost_micros / 1_000_000:.2f}")

print(f"\n✅ Total filas: {total_rows}")
