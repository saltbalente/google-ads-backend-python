#!/usr/bin/env python3
"""
Test del endpoint de quality-report corregido
"""
import os
from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv

load_dotenv()

# Configuración
CUSTOMER_ID = "7094116152"  # La cuenta que usa el usuario amarresyunionesdeamors@gmail.com

print("=" * 70)
print("TEST: Endpoint /api/keywords/quality-report CORREGIDO")
print("=" * 70)

# Crear cliente
credentials = {
    "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
    "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
    "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
    "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
    "use_proto_plus": True,
    "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "8531174172")
}

try:
    client = GoogleAdsClient.load_from_dict(credentials)
    service = client.get_service('GoogleAdsService')
    
    print(f"\n📊 Customer ID: {CUSTOMER_ID}")
    print(f"🔑 Login Customer ID: {credentials['login_customer_id']}")
    
    # Query CORREGIDA - usando keyword_view en vez de ad_group_criterion
    query = """
        SELECT 
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.quality_info.quality_score,
            ad_group_criterion.quality_info.creative_quality_score,
            ad_group_criterion.quality_info.post_click_quality_score,
            ad_group_criterion.quality_info.search_predicted_ctr,
            ad_group_criterion.final_urls,
            ad_group.id,
            ad_group.name,
            campaign.id,
            campaign.name,
            metrics.conversions,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks
        FROM keyword_view
        WHERE 
            ad_group_criterion.type = 'KEYWORD' 
            AND ad_group_criterion.status = 'ENABLED'
            AND campaign.status = 'ENABLED'
            AND ad_group.status = 'ENABLED'
        LIMIT 10
    """
    
    print("\n🔍 Ejecutando query...")
    print("-" * 70)
    
    rows = service.search(customer_id=CUSTOMER_ID, query=query)
    
    keywords_found = 0
    for row in rows:
        keywords_found += 1
        kw = row.ad_group_criterion
        metrics = row.metrics
        
        print(f"\n📌 Keyword {keywords_found}:")
        print(f"   ID: {kw.criterion_id}")
        print(f"   Texto: {kw.keyword.text}")
        print(f"   Match Type: {kw.keyword.match_type.name}")
        print(f"   Quality Score: {kw.quality_info.quality_score if kw.quality_info.quality_score else 'N/A'}")
        print(f"   Ad Relevance: {kw.quality_info.creative_quality_score.name}")
        print(f"   Landing Page Exp: {kw.quality_info.post_click_quality_score.name}")
        print(f"   Expected CTR: {kw.quality_info.search_predicted_ctr.name}")
        print(f"   Campaign: {row.campaign.name} (ID: {row.campaign.id})")
        print(f"   Ad Group: {row.ad_group.name} (ID: {row.ad_group.id})")
        print(f"   Métricas:")
        print(f"     - Impresiones: {metrics.impressions}")
        print(f"     - Clicks: {metrics.clicks}")
        print(f"     - Conversiones: {metrics.conversions}")
        print(f"     - Costo: ${metrics.cost_micros / 1_000_000:.2f}")
    
    print("\n" + "=" * 70)
    if keywords_found > 0:
        print(f"✅ SUCCESS: Se encontraron {keywords_found} keywords con métricas")
        print("✅ La query funciona correctamente usando keyword_view")
    else:
        print("⚠️  No se encontraron keywords (puede ser que no haya keywords activas)")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print(f"\n📝 Tipo de error: {type(e).__name__}")
    
    # Detalles adicionales
    if hasattr(e, 'error'):
        print(f"\n🔍 Detalles del error:")
        print(e.error)
