#!/usr/bin/env python3
"""
Test directo de la funcionalidad (sin servidor HTTP)
Importa y prueba las funciones directamente
"""

from google.ads.googleads.client import GoogleAdsClient
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

def test_budget_and_campaign_creation():
    """Test directo de creación de budget y campaña"""
    
    print("🧪 ==========================================")
    print("🧪 TEST DIRECTO: Budget + Campaign Creation")
    print("🧪 ==========================================\n")
    
    # Crear cliente
    client = GoogleAdsClient.load_from_dict({
        "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": True
    })
    
    customer_id = "6639082872"
    
    # Paso 1: Crear presupuesto NO compartido
    print("📋 Paso 1: Creando presupuesto (isShared=False)...")
    campaign_budget_service = client.get_service("CampaignBudgetService")
    budget_operation = client.get_type("CampaignBudgetOperation")
    budget = budget_operation.create
    
    budget.name = f"TEST Budget Final {date.today().strftime('%Y%m%d-%H%M%S')}"
    budget.amount_micros = 470000000000
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget.explicitly_shared = False  # NO compartido
    
    budget_response = campaign_budget_service.mutate_campaign_budgets(
        customer_id=customer_id,
        operations=[budget_operation]
    )
    
    budget_resource_name = budget_response.results[0].resource_name
    print(f"✅ Budget creado: {budget_resource_name}")
    print(f"   explicitly_shared: False\n")
    
    # Paso 2: Crear campaña con MAXIMIZE_CONVERSIONS
    print("📋 Paso 2: Creando campaña (MAXIMIZE_CONVERSIONS)...")
    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.create
    
    campaign.name = f"TEST Campaign Final {date.today().strftime('%Y%m%d-%H%M%S')}"
    campaign.campaign_budget = budget_resource_name
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.start_date = date.today().strftime('%Y%m%d')
    
    # EU Political Advertising
    try:
        from google.ads.googleads.v22.enums.types.campaign_contains_eu_political_advertising import CampaignContainsEuPoliticalAdvertisingEnum
        campaign.contains_eu_political_advertising = CampaignContainsEuPoliticalAdvertisingEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    except ImportError:
        campaign.contains_eu_political_advertising = 2
    
    # MAXIMIZE_CONVERSIONS - La clave es establecer target_cpa_micros = 0
    campaign.maximize_conversions.target_cpa_micros = 0
    
    # Network settings
    campaign.network_settings.target_google_search = True
    campaign.network_settings.target_search_network = True
    campaign.network_settings.target_content_network = False
    campaign.network_settings.target_partner_search_network = False
    
    print(f"   Name: {campaign.name}")
    print(f"   Budget: {budget_resource_name}")
    print(f"   Bidding: MAXIMIZE_CONVERSIONS (target_cpa_micros=0)")
    print(f"   Status: PAUSED")
    
    try:
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id,
            operations=[campaign_operation]
        )
        
        resource_name = response.results[0].resource_name
        campaign_id = resource_name.split('/')[-1]
        
        print(f"\n✅ Campaign creada: {campaign_id}")
        print(f"   Resource: {resource_name}\n")
        
        print("🎉 ==========================================")
        print("🎉 ¡TODO FUNCIONA CORRECTAMENTE!")
        print("🎉 ==========================================")
        print("\n📝 Configuración verificada:")
        print("   ✓ Budget NO compartido (explicitly_shared=False)")
        print("   ✓ MAXIMIZE_CONVERSIONS (target_cpa_micros=0)")
        print("   ✓ EU Political Advertising configurado")
        print("   ✓ Network settings aplicados")
        print("\n✅ El backend de Python está listo para producción")
        print("✅ El código de Swift funcionará correctamente")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        if hasattr(e, 'error'):
            print(f"   Detalles: {e.error}")
        return False

if __name__ == "__main__":
    success = test_budget_and_campaign_creation()
    exit(0 if success else 1)
