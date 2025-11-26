#!/usr/bin/env python3
"""
Script para probar localmente el query de demographics stats usando ad_group_criterion
"""
import os
import sys
from datetime import datetime, timedelta
from google.ads.googleads.client import GoogleAdsClient

def get_google_ads_client():
    """Crear cliente de Google Ads"""
    credentials = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET", ""),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN", ""),
        "use_proto_plus": True,
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
    }
    return GoogleAdsClient.load_from_dict(credentials)

def test_demographics_stats(customer_id, ad_group_id, days=7):
    """Probar queries de demographics usando ad_group_criterion"""
    print(f"\n{'='*60}")
    print(f"🧪 PRUEBA DE DEMOGRAPHICS STATS")
    print(f"{'='*60}")
    print(f"Customer ID: {customer_id}")
    print(f"Ad Group ID: {ad_group_id}")
    print(f"Periodo: últimos {days} días")
    print(f"{'='*60}\n")
    
    # Preparar fechas
    date_end = datetime.now().strftime('%Y-%m-%d')
    date_start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    print(f"📅 Rango de fechas: {date_start} a {date_end}\n")
    
    # Crear cliente
    try:
        client = get_google_ads_client()
        google_ads_service = client.get_service("GoogleAdsService")
        print("✅ Cliente de Google Ads creado correctamente\n")
    except Exception as e:
        print(f"❌ Error creando cliente: {e}")
        return
    
    # Test 1: Query de género usando ad_group_criterion
    print("="*60)
    print("TEST 1: GÉNERO - ad_group_criterion")
    print("="*60)
    
    gender_ids = ["10", "11", "20"]  # Female, Male, Undetermined
    gender_stats = {}
    
    for gender_id in gender_ids:
        try:
            query = f"""
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.gender.type,
                    ad_group_criterion.negative,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros
                FROM ad_group_criterion
                WHERE ad_group_criterion.ad_group = 'customers/{customer_id}/adGroups/{ad_group_id}'
                    AND ad_group_criterion.type = 'GENDER'
                    AND ad_group_criterion.criterion_id = {gender_id}
                    AND ad_group_criterion.status = 'ENABLED'
                    AND segments.date BETWEEN '{date_start}' AND '{date_end}'
            """
            
            print(f"\n🔍 Consultando género {gender_id}...")
            response = google_ads_service.search(customer_id=customer_id, query=query)
            
            row_count = 0
            for row in response:
                row_count += 1
                criterion_id = str(row.ad_group_criterion.criterion_id)
                gender_type = row.ad_group_criterion.gender.type.name
                is_negative = row.ad_group_criterion.negative
                
                if criterion_id not in gender_stats:
                    gender_stats[criterion_id] = {
                        "type": gender_type,
                        "conversions": 0,
                        "clicks": 0,
                        "impressions": 0,
                        "cost": 0,
                        "isNegative": is_negative
                    }
                
                gender_stats[criterion_id]["conversions"] += row.metrics.conversions
                gender_stats[criterion_id]["clicks"] += row.metrics.clicks
                gender_stats[criterion_id]["impressions"] += row.metrics.impressions
                gender_stats[criterion_id]["cost"] += row.metrics.cost_micros / 1_000_000
                
                print(f"   ✅ {gender_type} (ID: {criterion_id})")
                print(f"      Conversiones: {row.metrics.conversions}")
                print(f"      Clicks: {row.metrics.clicks}")
                print(f"      Impresiones: {row.metrics.impressions}")
                print(f"      Costo: ${row.metrics.cost_micros / 1_000_000:.2f}")
                print(f"      Negativo: {is_negative}")
            
            if row_count == 0:
                print(f"   ⚠️  No hay datos para género {gender_id}")
                
        except Exception as e:
            print(f"   ❌ Error en género {gender_id}: {e}")
    
    print(f"\n📊 RESUMEN GÉNERO: {len(gender_stats)} segmentos con datos")
    for gid, data in gender_stats.items():
        print(f"   {data['type']} ({gid}): {data['conversions']} conv, {data['clicks']} clicks, {data['impressions']} impr")
    
    # Test 2: Query de edad usando ad_group_criterion
    print("\n" + "="*60)
    print("TEST 2: EDAD - ad_group_criterion")
    print("="*60)
    
    age_ids = ["503001", "503002", "503003", "503004", "503005", "503006", "503999"]
    age_stats = {}
    
    for age_id in age_ids:
        try:
            query = f"""
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.age_range.type,
                    ad_group_criterion.negative,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros
                FROM ad_group_criterion
                WHERE ad_group_criterion.ad_group = 'customers/{customer_id}/adGroups/{ad_group_id}'
                    AND ad_group_criterion.type = 'AGE_RANGE'
                    AND ad_group_criterion.criterion_id = {age_id}
                    AND ad_group_criterion.status = 'ENABLED'
                    AND segments.date BETWEEN '{date_start}' AND '{date_end}'
            """
            
            print(f"\n🔍 Consultando edad {age_id}...")
            response = google_ads_service.search(customer_id=customer_id, query=query)
            
            row_count = 0
            for row in response:
                row_count += 1
                criterion_id = str(row.ad_group_criterion.criterion_id)
                age_type = row.ad_group_criterion.age_range.type.name
                is_negative = row.ad_group_criterion.negative
                
                if criterion_id not in age_stats:
                    age_stats[criterion_id] = {
                        "type": age_type,
                        "conversions": 0,
                        "clicks": 0,
                        "impressions": 0,
                        "cost": 0,
                        "isNegative": is_negative
                    }
                
                age_stats[criterion_id]["conversions"] += row.metrics.conversions
                age_stats[criterion_id]["clicks"] += row.metrics.clicks
                age_stats[criterion_id]["impressions"] += row.metrics.impressions
                age_stats[criterion_id]["cost"] += row.metrics.cost_micros / 1_000_000
                
                print(f"   ✅ {age_type} (ID: {criterion_id})")
                print(f"      Conversiones: {row.metrics.conversions}")
                print(f"      Clicks: {row.metrics.clicks}")
                print(f"      Impresiones: {row.metrics.impressions}")
                print(f"      Costo: ${row.metrics.cost_micros / 1_000_000:.2f}")
                
            if row_count == 0:
                print(f"   ⚠️  No hay datos para edad {age_id}")
                
        except Exception as e:
            print(f"   ❌ Error en edad {age_id}: {e}")
    
    print(f"\n📊 RESUMEN EDAD: {len(age_stats)} segmentos con datos")
    for aid, data in age_stats.items():
        print(f"   {data['type']} ({aid}): {data['conversions']} conv, {data['clicks']} clicks, {data['impressions']} impr")
    
    # Test 3: Query de ingreso usando ad_group_criterion
    print("\n" + "="*60)
    print("TEST 3: INGRESO - ad_group_criterion")
    print("="*60)
    
    income_ids = ["31000", "31001", "31002", "31003", "31004", "31005", "31006"]
    income_stats = {}
    
    for income_id in income_ids:
        try:
            query = f"""
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.income_range.type,
                    ad_group_criterion.negative,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros
                FROM ad_group_criterion
                WHERE ad_group_criterion.ad_group = 'customers/{customer_id}/adGroups/{ad_group_id}'
                    AND ad_group_criterion.type = 'INCOME_RANGE'
                    AND ad_group_criterion.criterion_id = {income_id}
                    AND ad_group_criterion.status = 'ENABLED'
                    AND segments.date BETWEEN '{date_start}' AND '{date_end}'
            """
            
            print(f"\n🔍 Consultando ingreso {income_id}...")
            response = google_ads_service.search(customer_id=customer_id, query=query)
            
            row_count = 0
            for row in response:
                row_count += 1
                criterion_id = str(row.ad_group_criterion.criterion_id)
                income_type = row.ad_group_criterion.income_range.type.name
                is_negative = row.ad_group_criterion.negative
                
                if criterion_id not in income_stats:
                    income_stats[criterion_id] = {
                        "type": income_type,
                        "conversions": 0,
                        "clicks": 0,
                        "impressions": 0,
                        "cost": 0,
                        "isNegative": is_negative
                    }
                
                income_stats[criterion_id]["conversions"] += row.metrics.conversions
                income_stats[criterion_id]["clicks"] += row.metrics.clicks
                income_stats[criterion_id]["impressions"] += row.metrics.impressions
                income_stats[criterion_id]["cost"] += row.metrics.cost_micros / 1_000_000
                
                print(f"   ✅ {income_type} (ID: {criterion_id})")
                print(f"      Conversiones: {row.metrics.conversions}")
                print(f"      Clicks: {row.metrics.clicks}")
                print(f"      Impresiones: {row.metrics.impressions}")
                print(f"      Costo: ${row.metrics.cost_micros / 1_000_000:.2f}")
                
            if row_count == 0:
                print(f"   ⚠️  No hay datos para ingreso {income_id}")
                
        except Exception as e:
            print(f"   ❌ Error en ingreso {income_id}: {e}")
    
    print(f"\n📊 RESUMEN INGRESO: {len(income_stats)} segmentos con datos")
    for iid, data in income_stats.items():
        print(f"   {data['type']} ({iid}): {data['conversions']} conv, {data['clicks']} clicks, {data['impressions']} impr")
    
    # Resumen final
    print("\n" + "="*60)
    print("📈 RESULTADO FINAL")
    print("="*60)
    print(f"Género: {len(gender_stats)} segmentos")
    print(f"Edad: {len(age_stats)} segmentos")
    print(f"Ingreso: {len(income_stats)} segmentos")
    
    total_conversions = sum(s["conversions"] for s in gender_stats.values())
    total_clicks = sum(s["clicks"] for s in gender_stats.values())
    total_impressions = sum(s["impressions"] for s in gender_stats.values())
    
    print(f"\nTotales (género):")
    print(f"  Conversiones: {total_conversions}")
    print(f"  Clicks: {total_clicks}")
    print(f"  Impresiones: {total_impressions}")
    
    if total_conversions > 0 or total_clicks > 0 or total_impressions > 0:
        print("\n✅ ¡ÉXITO! El query ad_group_criterion está devolviendo datos reales")
    else:
        print("\n⚠️  No se encontraron métricas. Verifica que el ad group tenga datos en este periodo.")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    # Parámetros de prueba
    CUSTOMER_ID = "5852810891"
    AD_GROUP_ID = "175024723431"  # "Grupo de anuncios 1"
    DAYS = 7
    
    test_demographics_stats(CUSTOMER_ID, AD_GROUP_ID, DAYS)
