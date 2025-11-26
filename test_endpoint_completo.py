#!/usr/bin/env python3
"""
Test del endpoint completo de demographics stats con el nuevo código
"""
import os
import sys
from datetime import datetime, timedelta

# Agregar el directorio al path
sys.path.insert(0, '/Users/edwarbechara/Documents/app-reportes-pagos-BACKUP-20250702-123421/google-ads-backend-python')

# Cargar variables de entorno
os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"] = "Kqg431In6DxoZnSMJk0hQg"
os.environ["GOOGLE_ADS_CLIENT_ID"] = "82393641971-edkinpiigpprkbdi0dtnalem8ndo5c1j.apps.googleusercontent.com"
os.environ["GOOGLE_ADS_CLIENT_SECRET"] = "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"
os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"] = "8531174172"
os.environ["GOOGLE_ADS_REFRESH_TOKEN"] = "1//05qNlWCfgnPRZCgYIARAAGAUSNwF-L9IrPwBJ2CdrABme75Bk-RUU-8WeYGiFsTkqatFijKG-ckHpqyfPRlQI68LTGWbN54JyUAY"

from google.ads.googleads.client import GoogleAdsClient

def get_google_ads_client():
    credentials = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "use_proto_plus": True,
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    }
    return GoogleAdsClient.load_from_dict(credentials)

# Simular el código del endpoint
customer_id = "5852810891"
ad_group_id = "175024723431"
days = 7

date_end = datetime.now().strftime('%Y-%m-%d')
date_start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

print(f"\n🧪 TEST DEL ENDPOINT COMPLETO")
print(f"Customer: {customer_id}")
print(f"Ad Group: {ad_group_id}")
print(f"Periodo: {date_start} a {date_end}")
print("="*60 + "\n")

client = get_google_ads_client()
google_ads_service = client.get_service("GoogleAdsService")

stats = {
    "gender": {},
    "age": {},
    "income": {}
}

# GÉNERO
try:
    gender_query = f"""
        SELECT
            gender_view.resource_name,
            metrics.conversions,
            metrics.conversions_value,
            metrics.clicks,
            metrics.impressions,
            metrics.cost_micros
        FROM gender_view
        WHERE ad_group.id = {ad_group_id}
            AND segments.date BETWEEN '{date_start}' AND '{date_end}'
    """
    
    gender_response = google_ads_service.search(customer_id=customer_id, query=gender_query)
    
    for row in gender_response:
        resource_name = row.gender_view.resource_name
        criterion_id = resource_name.split('~')[-1]
        
        if criterion_id not in stats["gender"]:
            stats["gender"][criterion_id] = {
                "conversions": 0,
                "conversionsValue": 0,
                "clicks": 0,
                "impressions": 0,
                "cost": 0,
                "isNegative": False
            }
        
        stats["gender"][criterion_id]["conversions"] += row.metrics.conversions
        stats["gender"][criterion_id]["conversionsValue"] += row.metrics.conversions_value
        stats["gender"][criterion_id]["clicks"] += row.metrics.clicks
        stats["gender"][criterion_id]["impressions"] += row.metrics.impressions
        stats["gender"][criterion_id]["cost"] += row.metrics.cost_micros / 1_000_000
    
    print(f"✅ Gender: {len(stats['gender'])} segmentos")
except Exception as e:
    print(f"❌ Error en género: {e}")

# EDAD
try:
    age_query = f"""
        SELECT
            age_range_view.resource_name,
            metrics.conversions,
            metrics.conversions_value,
            metrics.clicks,
            metrics.impressions,
            metrics.cost_micros
        FROM age_range_view
        WHERE ad_group.id = {ad_group_id}
            AND segments.date BETWEEN '{date_start}' AND '{date_end}'
    """
    
    age_response = google_ads_service.search(customer_id=customer_id, query=age_query)
    
    for row in age_response:
        resource_name = row.age_range_view.resource_name
        criterion_id = resource_name.split('~')[-1]
        
        if criterion_id not in stats["age"]:
            stats["age"][criterion_id] = {
                "conversions": 0,
                "conversionsValue": 0,
                "clicks": 0,
                "impressions": 0,
                "cost": 0,
                "isNegative": False
            }
        
        stats["age"][criterion_id]["conversions"] += row.metrics.conversions
        stats["age"][criterion_id]["conversionsValue"] += row.metrics.conversions_value
        stats["age"][criterion_id]["clicks"] += row.metrics.clicks
        stats["age"][criterion_id]["impressions"] += row.metrics.impressions
        stats["age"][criterion_id]["cost"] += row.metrics.cost_micros / 1_000_000
    
    print(f"✅ Age: {len(stats['age'])} segmentos")
except Exception as e:
    print(f"❌ Error en edad: {e}")

# INGRESO
try:
    income_id_map = {
        "510000": "31006",
        "510001": "31005",
        "510002": "31004",
        "510003": "31003",
        "510004": "31002",
        "510005": "31001",
        "510006": "31000",
    }
    
    income_query = f"""
        SELECT
            income_range_view.resource_name,
            metrics.conversions,
            metrics.conversions_value,
            metrics.clicks,
            metrics.impressions,
            metrics.cost_micros
        FROM income_range_view
        WHERE ad_group.id = {ad_group_id}
            AND segments.date BETWEEN '{date_start}' AND '{date_end}'
    """
    
    income_response = google_ads_service.search(customer_id=customer_id, query=income_query)
    
    for row in income_response:
        resource_name = row.income_range_view.resource_name
        api_id = resource_name.split('~')[-1]
        criterion_id = income_id_map.get(api_id, api_id)
        
        if criterion_id not in stats["income"]:
            stats["income"][criterion_id] = {
                "conversions": 0,
                "conversionsValue": 0,
                "clicks": 0,
                "impressions": 0,
                "cost": 0,
                "isNegative": False
            }
        
        stats["income"][criterion_id]["conversions"] += row.metrics.conversions
        stats["income"][criterion_id]["conversionsValue"] += row.metrics.conversions_value
        stats["income"][criterion_id]["clicks"] += row.metrics.clicks
        stats["income"][criterion_id]["impressions"] += row.metrics.impressions
        stats["income"][criterion_id]["cost"] += row.metrics.cost_micros / 1_000_000
    
    print(f"✅ Income: {len(stats['income'])} segmentos")
except Exception as e:
    print(f"❌ Error en ingreso: {e}")

# Resultado final
print("\n" + "="*60)
print("📊 RESULTADO FINAL (formato JSON)")
print("="*60)

import json
result = {
    "success": True,
    "stats": stats,
    "dateRange": {
        "start": date_start,
        "end": date_end,
        "days": days
    }
}

print(json.dumps(result, indent=2))

# Verificar que hay datos
total_conv = sum(s["conversions"] for s in stats["gender"].values())
total_clicks = sum(s["clicks"] for s in stats["gender"].values())

if total_conv > 0 or total_clicks > 0:
    print("\n✅ ¡ÉXITO! El endpoint devuelve datos reales")
else:
    print("\n⚠️ No hay conversiones ni clicks en este periodo")
