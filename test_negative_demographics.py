#!/usr/bin/env python3
"""
Script de prueba para verificar si Google Ads permite negative targeting de demografía
en ad groups (grupos de anuncios).

Prueba: Excluir "Hombres" (11) y "Edad Desconocida" (503999)
"""

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from dotenv import load_dotenv
import os
import json

# Cargar variables de entorno
load_dotenv()

def get_google_ads_client():
    """Crea cliente de Google Ads desde variables de entorno"""
    return GoogleAdsClient.load_from_dict({
        "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": True
    })

def test_negative_demographic_targeting():
    """
    Intenta crear criterios negativos de demografía en un ad group.
    """
    customer_id = "5753767756"
    ad_group_id = "166462715675"
    
    print(f"🧪 Probando negative targeting en Ad Group {ad_group_id}")
    print("=" * 60)
    
    client = get_google_ads_client()
    ad_group_criterion_service = client.get_service("AdGroupCriterionService")
    
    ad_group_path = f"customers/{customer_id}/adGroups/{ad_group_id}"
    
    operations = []
    
    # Prueba 1: Intentar excluir "Hombres" (MALE = 11)
    print("\n📝 Prueba 1: Excluir HOMBRES (gender = 11, negative = True)")
    operation1 = client.get_type("AdGroupCriterionOperation")
    criterion1 = operation1.create
    criterion1.ad_group = ad_group_path
    criterion1.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    criterion1.negative = True  # EXCLUSIÓN
    criterion1.gender.type_ = client.enums.GenderTypeEnum.MALE
    operations.append(operation1)
    
    # Prueba 2: Intentar excluir "Edad Desconocida" (AGE_RANGE_UNDETERMINED = 503999)
    print("📝 Prueba 2: Excluir EDAD DESCONOCIDA (age = 503999, negative = True)")
    operation2 = client.get_type("AdGroupCriterionOperation")
    criterion2 = operation2.create
    criterion2.ad_group = ad_group_path
    criterion2.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    criterion2.negative = True  # EXCLUSIÓN
    criterion2.age_range.type_ = client.enums.AgeRangeTypeEnum.AGE_RANGE_UNDETERMINED
    operations.append(operation2)
    
    # Prueba 3: Como control, agregar "Mujeres" (FEMALE = 10) como positivo
    print("📝 Prueba 3 (Control): Incluir MUJERES (gender = 10, negative = False)")
    operation3 = client.get_type("AdGroupCriterionOperation")
    criterion3 = operation3.create
    criterion3.ad_group = ad_group_path
    criterion3.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    criterion3.negative = False  # INCLUSIÓN (normal)
    criterion3.gender.type_ = client.enums.GenderTypeEnum.FEMALE
    operations.append(operation3)
    
    print("\n" + "=" * 60)
    print("🚀 Ejecutando operaciones...")
    print("=" * 60)
    
    try:
        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id,
            operations=operations
        )
        
        print("\n✅ ¡ÉXITO! Las operaciones se ejecutaron correctamente.")
        print(f"Total de criterios creados: {len(response.results)}")
        print("\nDetalles de los criterios creados:")
        for i, result in enumerate(response.results, 1):
            print(f"  {i}. {result.resource_name}")
        
        print("\n" + "=" * 60)
        print("📊 CONCLUSIÓN:")
        print("Google Ads SÍ permite negative targeting de demografía en ad groups.")
        print("=" * 60)
        
        return True
        
    except GoogleAdsException as ex:
        print("\n❌ ERROR: La operación falló")
        print("=" * 60)
        
        for error in ex.failure.errors:
            print(f"\n🔴 Error Code: {error.error_code}")
            print(f"📝 Mensaje: {error.message}")
            
            if hasattr(error, 'location'):
                print(f"📍 Ubicación: {error.location}")
            
            # Detalles del error en JSON
            try:
                error_dict = {
                    "error_code": error.error_code.to_json() if hasattr(error, 'error_code') else str(error.error_code),
                    "message": error.message,
                    "trigger": error.trigger.string_value if hasattr(error, 'trigger') else None
                }
                print(f"\n📋 JSON completo del error:")
                print(json.dumps(error_dict, indent=2))
            except:
                pass
        
        print("\n" + "=" * 60)
        print("📊 CONCLUSIÓN:")
        print("Google Ads NO permite negative targeting de demografía en ad groups,")
        print("o hay algún error en la forma de crear los criterios.")
        print("=" * 60)
        
        return False

if __name__ == "__main__":
    print("\n" + "🧪 TEST: NEGATIVE DEMOGRAPHIC TARGETING EN AD GROUPS ".center(60, "="))
    print()
    
    test_negative_demographic_targeting()
    
    print("\n" + "FIN DEL TEST ".center(60, "=") + "\n")
