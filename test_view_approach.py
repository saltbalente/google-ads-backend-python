#!/usr/bin/env python3
"""
Probar el enfoque CORRECTO: usar gender_view, age_range_view, income_range_view
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

print(f"\n🧪 TEST: gender_view, age_range_view, income_range_view")
print(f"Periodo: {date_start} a {date_end}\n")

client = get_client()
service = client.get_service("GoogleAdsService")

# TEST 1: gender_view
print("="*60)
print("TEST 1: gender_view")
print("="*60)
query = f"""
    SELECT
        ad_group.id,
        gender_view.resource_name,
        metrics.conversions,
        metrics.clicks,
        metrics.impressions,
        metrics.cost_micros
    FROM gender_view
    WHERE ad_group.id = {ad_group_id}
        AND segments.date BETWEEN '{date_start}' AND '{date_end}'
"""

print("Ejecutando query...")
try:
    response = service.search(customer_id=customer_id, query=query)
    row_count = 0
    for row in response:
        row_count += 1
        print(f"\n  Resource: {row.gender_view.resource_name}")
        print(f"  Ad Group: {row.ad_group.id}")
        print(f"  Conversiones: {row.metrics.conversions}")
        print(f"  Clicks: {row.metrics.clicks}")
        print(f"  Impresiones: {row.metrics.impressions}")
        print(f"  Costo: ${row.metrics.cost_micros / 1_000_000:.2f}")
    
    if row_count == 0:
        print("  ⚠️  No hay datos")
    else:
        print(f"\n✅ Total filas: {row_count}")
except Exception as e:
    print(f"❌ Error: {e}")

# TEST 2: age_range_view
print("\n" + "="*60)
print("TEST 2: age_range_view")
print("="*60)
query = f"""
    SELECT
        ad_group.id,
        age_range_view.resource_name,
        metrics.conversions,
        metrics.clicks,
        metrics.impressions,
        metrics.cost_micros
    FROM age_range_view
    WHERE ad_group.id = {ad_group_id}
        AND segments.date BETWEEN '{date_start}' AND '{date_end}'
"""

print("Ejecutando query...")
try:
    response = service.search(customer_id=customer_id, query=query)
    row_count = 0
    for row in response:
        row_count += 1
        print(f"\n  Resource: {row.age_range_view.resource_name}")
        print(f"  Ad Group: {row.ad_group.id}")
        print(f"  Conversiones: {row.metrics.conversions}")
        print(f"  Clicks: {row.metrics.clicks}")
        print(f"  Impresiones: {row.metrics.impressions}")
        print(f"  Costo: ${row.metrics.cost_micros / 1_000_000:.2f}")
    
    if row_count == 0:
        print("  ⚠️  No hay datos")
    else:
        print(f"\n✅ Total filas: {row_count}")
except Exception as e:
    print(f"❌ Error: {e}")

# TEST 3: income_range_view
print("\n" + "="*60)
print("TEST 3: income_range_view")
print("="*60)
query = f"""
    SELECT
        ad_group.id,
        income_range_view.resource_name,
        metrics.conversions,
        metrics.clicks,
        metrics.impressions,
        metrics.cost_micros
    FROM income_range_view
    WHERE ad_group.id = {ad_group_id}
        AND segments.date BETWEEN '{date_start}' AND '{date_end}'
"""

print("Ejecutando query...")
try:
    response = service.search(customer_id=customer_id, query=query)
    row_count = 0
    for row in response:
        row_count += 1
        print(f"\n  Resource: {row.income_range_view.resource_name}")
        print(f"  Ad Group: {row.ad_group.id}")
        print(f"  Conversiones: {row.metrics.conversions}")
        print(f"  Clicks: {row.metrics.clicks}")
        print(f"  Impresiones: {row.metrics.impressions}")
        print(f"  Costo: ${row.metrics.cost_micros / 1_000_000:.2f}")
    
    if row_count == 0:
        print("  ⚠️  No hay datos")
    else:
        print(f"\n✅ Total filas: {row_count}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*60)
