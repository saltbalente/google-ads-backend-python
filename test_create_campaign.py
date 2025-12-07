#!/usr/bin/env python3
"""
Script de prueba local para crear campaña con MAXIMIZE_CONVERSIONS
"""

from google.ads.googleads.client import GoogleAdsClient
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

def test_create_campaign():
    """Prueba la creación de campaña con MAXIMIZE_CONVERSIONS"""
    
    # Crear cliente
    client = GoogleAdsClient.load_from_dict({
        "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": True
    })
    
    customer_id = "6639082872"  # Tu customer ID
    
    print("🧪 TEST: Creando campaña de prueba con MAXIMIZE_CONVERSIONS")
    print(f"Customer ID: {customer_id}")
    
    # Paso 1: Crear presupuesto NO compartido
    print("\n📋 Paso 1: Creando presupuesto...")
    campaign_budget_service = client.get_service("CampaignBudgetService")
    budget_operation = client.get_type("CampaignBudgetOperation")
    budget = budget_operation.create
    
    budget.name = f"TEST Budget {date.today().strftime('%Y%m%d-%H%M%S')}"
    budget.amount_micros = 470000000000  # $470,000 COP
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget.explicitly_shared = False  # NO compartido (crítico para MAXIMIZE_CONVERSIONS)
    
    budget_response = campaign_budget_service.mutate_campaign_budgets(
        customer_id=customer_id,
        operations=[budget_operation]
    )
    
    budget_resource_name = budget_response.results[0].resource_name
    print(f"✅ Budget creado: {budget_resource_name}")
    print(f"   Shared: False")
    
    # Paso 2: Crear campaña con MAXIMIZE_CONVERSIONS
    print("\n📋 Paso 2: Creando campaña...")
    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.create
    
    campaign.name = f"TEST Campaign MAXIMIZE_CONVERSIONS {date.today().strftime('%Y%m%d-%H%M%S')}"
    campaign.campaign_budget = budget_resource_name
    campaign.status = client.enums.CampaignStatusEnum.PAUSED  # PAUSED para prueba
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.start_date = date.today().strftime('%Y%m%d')
    
    # EU Political Advertising
    try:
        from google.ads.googleads.v22.enums.types.campaign_contains_eu_political_advertising import CampaignContainsEuPoliticalAdvertisingEnum
        campaign.contains_eu_political_advertising = CampaignContainsEuPoliticalAdvertisingEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    except ImportError:
        campaign.contains_eu_political_advertising = 2
    
    # Estrategia MAXIMIZE_CONVERSIONS
    print("   Configurando MAXIMIZE_CONVERSIONS...")
    # Establecer target_cpa_micros en 0 (sin target, optimización automática)
    campaign.maximize_conversions.target_cpa_micros = 0
    
    # Network settings
    campaign.network_settings.target_google_search = True
    campaign.network_settings.target_search_network = True
    campaign.network_settings.target_content_network = False
    campaign.network_settings.target_partner_search_network = False
    
    print(f"\n📊 Datos de la campaña:")
    print(f"   Name: {campaign.name}")
    print(f"   Budget: {budget_resource_name}")
    print(f"   Status: PAUSED")
    print(f"   Bidding: MAXIMIZE_CONVERSIONS")
    print(f"   EU Political: {campaign.contains_eu_political_advertising}")
    
    try:
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id,
            operations=[campaign_operation]
        )
        
        resource_name = response.results[0].resource_name
        campaign_id = resource_name.split('/')[-1]
        
        print(f"\n✅ ¡ÉXITO! Campaña creada:")
        print(f"   Resource Name: {resource_name}")
        print(f"   Campaign ID: {campaign_id}")
        print(f"\n🎉 El backend funcionará correctamente con esta configuración")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"\n🔍 Detalles del error:")
        if hasattr(e, 'error'):
            print(f"   {e.error}")
        return False

if __name__ == "__main__":
    success = test_create_campaign()
    exit(0 if success else 1)
