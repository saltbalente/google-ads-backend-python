from flask import Flask, request, jsonify
from google.ads.googleads.client import GoogleAdsClient
from datetime import date, timedelta
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf.field_mask_pb2 import FieldMask
from circuit_breaker import circuit_breaker_bp, start_circuit_breaker_scheduler
from dotenv import load_dotenv
import os
from PIL import Image
import base64
from io import BytesIO
import json
import requests
import unicodedata
from pytrends.request import TrendReq

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_unexpected_error(e):
    res = jsonify({"success": False, "message": str(e)})
    res.status_code = 500
    res.headers.add('Access-Control-Allow-Origin', '*')
    res.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    res.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return res

def get_google_ads_client(refresh_token=None, login_customer_id=None):
    """Crea cliente de Google Ads. Prioriza credenciales pasadas, sino usa variables de entorno"""
    
    # Si viene refresh_token en los parámetros, es un usuario custom (iOS)
    # Usar Client ID de iOS (sin client_secret)
    if refresh_token and refresh_token != os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"):
        # Cliente iOS - NO requiere client_secret
        return GoogleAdsClient.load_from_dict({
            "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
            "client_id": "82393641971-2qpch75fpo28p7dmpqcibbp0vk6aj0g9.apps.googleusercontent.com",  # iOS Client ID
            "client_secret": "",  # iOS Client no tiene secret, pero la librería lo requiere
            "refresh_token": refresh_token,
            "login_customer_id": login_customer_id,
            "use_proto_plus": True
        })
    
    # Usuario default - usar credenciales del .env (Web Client con secret)
    return GoogleAdsClient.load_from_dict({
        "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": refresh_token or os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": login_customer_id or os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": True
    })

def get_client_from_request():
    """Helper para extraer credenciales de los headers y crear cliente"""
    refresh_token = request.headers.get('X-Google-Ads-Refresh-Token')
    login_customer_id = request.headers.get('X-Google-Ads-Login-Customer-Id')
    return get_google_ads_client(refresh_token, login_customer_id)

@app.route('/api/health', methods=['GET'])
def health():
    """Endpoint de salud"""
    configured = all([
        os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
        os.environ.get("GOOGLE_ADS_CLIENT_ID"),
        os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
        os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
        os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    ])
    
    return jsonify({
        "status": "ok",
        "service": "Google Ads Backend API (Python)",
        "version": "2.0.0",
        "configured": configured
    })

@app.route('/api/ai/health', methods=['GET'])
def ai_health():
    openai_ok = bool(os.environ.get('OPENAI_API_KEY'))
    gemini_ok = bool(os.environ.get('GOOGLE_API_KEY'))
    deepseek_ok = bool(os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPEN_ROUTER_API_KEY'))
    return jsonify({
        "status": "ok",
        "providers": {
            "openai": {"configured": openai_ok, "model": os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')},
            "gemini": {"configured": gemini_ok},
            "deepseek": {"configured": deepseek_ok, "model": os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')}
        }
    })

@app.route('/api/create-ad', methods=['POST', 'OPTIONS'])
def create_ad():
    """Crea un anuncio de búsqueda responsive"""
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId')
        ad_group_id = data.get('adGroupId')
        headlines = data.get('headlines', [])
        descriptions = data.get('descriptions', [])
        final_url = data.get('finalUrl')
        
        # Eliminar duplicados manteniendo el orden
        # Google Ads API rechaza assets duplicados en la misma operación
        seen_headlines = set()
        unique_headlines = []
        for h in headlines:
            if h not in seen_headlines:
                seen_headlines.add(h)
                unique_headlines.append(h)
        
        seen_descriptions = set()
        unique_descriptions = []
        for d in descriptions:
            if d not in seen_descriptions:
                seen_descriptions.add(d)
                unique_descriptions.append(d)
        
        headlines = unique_headlines
        descriptions = unique_descriptions
        
        print(f"📝 Headlines después de eliminar duplicados: {len(headlines)} (originales: {len(data.get('headlines', []))})")
        print(f"📝 Descriptions después de eliminar duplicados: {len(descriptions)} (originales: {len(data.get('descriptions', []))})")
        
        # Validaciones
        if not all([customer_id, ad_group_id, headlines, descriptions, final_url]):
            return jsonify({
                "success": False,
                "error": "Faltan campos requeridos"
            }), 400
        
        if not (3 <= len(headlines) <= 15):
            return jsonify({
                "success": False,
                "error": f"Headlines debe tener entre 3-15 elementos (recibidos: {len(headlines)})"
            }), 400
        
        if not (2 <= len(descriptions) <= 4):
            return jsonify({
                "success": False,
                "error": f"Descriptions debe tener entre 2-4 elementos (recibidos: {len(descriptions)})"
            }), 400
        
        # Crear cliente
        refresh_token = request.headers.get('X-Google-Ads-Refresh-Token')
        login_customer_id = request.headers.get('X-Google-Ads-Login-Customer-Id')
        client = get_google_ads_client(refresh_token, login_customer_id)
        
        ad_group_ad_service = client.get_service("AdGroupAdService")
        ad_group_service = client.get_service("AdGroupService")
        
        # Crear operación
        ad_group_ad_operation = client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_group_ad_operation.create
        ad_group_ad.ad_group = ad_group_service.ad_group_path(customer_id, ad_group_id)
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
        
        # Configurar anuncio
        ad_group_ad.ad.final_urls.append(final_url)
        
        # Agregar títulos
        for headline_text in headlines:
            headline = client.get_type("AdTextAsset")
            headline.text = headline_text
            ad_group_ad.ad.responsive_search_ad.headlines.append(headline)
        
        # Agregar descripciones
        for description_text in descriptions:
            description = client.get_type("AdTextAsset")
            description.text = description_text
            ad_group_ad.ad.responsive_search_ad.descriptions.append(description)
        
        # Ejecutar mutación
        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=customer_id,
            operations=[ad_group_ad_operation]
        )
        
        resource_name = response.results[0].resource_name
        
        result = jsonify({
            "success": True,
            "resourceName": resource_name,
            "message": "Anuncio creado exitosamente en Google Ads (activado y listo)",
            "details": {
                "customerId": customer_id,
                "adGroupId": ad_group_id,
                "headlinesCount": len(headlines),
                "descriptionsCount": len(descriptions),
                "status": "ENABLED"
            }
        })
        
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        errors = []
        for error in ex.failure.errors:
            error_info = {
                "message": error.message,
                "error_code": str(error.error_code)
            }
            # Agregar detalles de políticas si existen
            if error.details and hasattr(error.details, 'policy_finding_details'):
                policy_topics = []
                for entry in error.details.policy_finding_details.policy_topic_entries:
                    policy_topics.append({
                        "type": str(entry.type_),
                        "topic": entry.topic
                    })
                error_info["policy_violations"] = policy_topics
            errors.append(error_info)
        
        result = jsonify({
            "success": False,
            "error": "Error de Google Ads API",
            "errors": errors,
            "request_id": ex.request_id
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as ex:
        result = jsonify({
            "success": False,
            "error": str(ex)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/demographics/get', methods=['POST', 'OPTIONS'])
def get_demographics():
    """Obtiene la configuración demográfica actual de un grupo de anuncios"""
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId')
        ad_group_id = data.get('adGroupId')
        
        if not all([customer_id, ad_group_id]):
            return jsonify({
                "success": False,
                "message": "Faltan customerId o adGroupId"
            }), 400
        
        # Crear cliente
        client = get_client_from_request()
        google_ads_service = client.get_service("GoogleAdsService")
        
        # Query para obtener criterios demográficos actuales
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.type,
                ad_group_criterion.gender.type,
                ad_group_criterion.age_range.type,
                ad_group_criterion.income_range.type,
                ad_group_criterion.negative
            FROM ad_group_criterion
            WHERE ad_group_criterion.ad_group = 'customers/{customer_id}/adGroups/{ad_group_id}'
                AND ad_group_criterion.type IN ('GENDER', 'AGE_RANGE', 'INCOME_RANGE')
                AND ad_group_criterion.status = 'ENABLED'
        """
        
        response = google_ads_service.search(customer_id=customer_id, query=query)
        
        genders = []
        genders_excluded = []
        age_ranges = []
        age_ranges_excluded = []
        household_incomes = []
        household_incomes_excluded = []
        
        for row in response:
            criterion = row.ad_group_criterion
            
            # Separar criterios positivos y negativos
            is_excluded = criterion.negative
            
            if criterion.type_.name == 'GENDER':
                gender_id = str(criterion.gender.type.value)
                if is_excluded:
                    if gender_id not in genders_excluded:
                        genders_excluded.append(gender_id)
                else:
                    if gender_id not in genders:
                        genders.append(gender_id)
            
            elif criterion.type_.name == 'AGE_RANGE':
                age_id = str(criterion.age_range.type.value)
                if is_excluded:
                    if age_id not in age_ranges_excluded:
                        age_ranges_excluded.append(age_id)
                else:
                    if age_id not in age_ranges:
                        age_ranges.append(age_id)
            
            elif criterion.type_.name == 'INCOME_RANGE':
                income_id = str(criterion.income_range.type.value)
                if is_excluded:
                    if income_id not in household_incomes_excluded:
                        household_incomes_excluded.append(income_id)
                else:
                    if income_id not in household_incomes:
                        household_incomes.append(income_id)
        
        # Si no hay criterios configurados, significa que TODOS están activos por defecto
        # (Google Ads sin restricciones = targeting a todos)
        if len(genders) == 0 and len(age_ranges) == 0 and len(household_incomes) == 0:
            print("⚠️ No hay criterios demográficos configurados - usando defaults (todos activos)")
            
            # Todos los géneros por defecto
            genders = ["10", "11", "20"]  # Mujer, Hombre, Desconocido
            
            # Todas las edades por defecto
            age_ranges = ["503001", "503002", "503003", "503004", "503005", "503006", "503999"]
            
            # Todos los ingresos por defecto
            household_incomes = ["31000", "31001", "31002", "31003", "31004", "31005", "31006"]
        
        print(f"✅ Demographics cargadas:")
        print(f"   Genders: {len(genders)} included, {len(genders_excluded)} excluded")
        print(f"   Ages: {len(age_ranges)} included, {len(age_ranges_excluded)} excluded")
        print(f"   Incomes: {len(household_incomes)} included, {len(household_incomes_excluded)} excluded")
        
        result = jsonify({
            "success": True,
            "message": "Configuración demográfica obtenida",
            "demographics": {
                "genders": genders,
                "gendersExcluded": genders_excluded,
                "ageRanges": age_ranges,
                "ageRangesExcluded": age_ranges_excluded,
                "householdIncomes": household_incomes,
                "householdIncomesExcluded": household_incomes_excluded
            }
        })
        
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        errors = [{"message": error.message} for error in ex.failure.errors]
        
        result = jsonify({
            "success": False,
            "message": "Error obteniendo demografía",
            "errors": errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as ex:
        result = jsonify({
            "success": False,
            "message": str(ex)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/demographics/update', methods=['POST', 'OPTIONS'])
def update_demographics():
    """Actualiza la configuración demográfica de un grupo de anuncios
    
    Los criterios activados (true) se crean como targeting positivo (incluir).
    Los criterios desactivados (false) se crean como targeting negativo (excluir).
    
    ✅ CONFIRMADO: Google Ads SÍ permite negative targeting de demografía en ad groups.
    """
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId')
        ad_group_id = data.get('adGroupId')
        
        # Recibir estados de todos los criterios ("included" = incluir, "excluded" = excluir, "notSet" = sin configurar)
        gender_states = data.get('genderStates', {})  # {"10": "included", "11": "excluded", "20": "notSet"}
        age_states = data.get('ageStates', {})
        income_states = data.get('incomeStates', {})
        
        if not all([customer_id, ad_group_id]):
            return jsonify({
                "success": False,
                "message": "Faltan customerId o adGroupId"
            }), 400
        
        # No validar si hay criterios - permitir vacío para remover todos
        
        # Crear cliente
        client = get_client_from_request()
        ad_group_criterion_service = client.get_service("AdGroupCriterionService")
        google_ads_service = client.get_service("GoogleAdsService")
        
        # Primero, obtener todos los criterios actuales
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.resource_name,
                ad_group_criterion.type
            FROM ad_group_criterion
            WHERE ad_group_criterion.ad_group = 'customers/{customer_id}/adGroups/{ad_group_id}'
                AND ad_group_criterion.type IN ('GENDER', 'AGE_RANGE', 'INCOME_RANGE')
        """
        
        current_response = google_ads_service.search(customer_id=customer_id, query=query)
        current_criteria = [row.ad_group_criterion.resource_name for row in current_response]
        
        operations = []
        
        # Eliminar todos los criterios actuales
        for resource_name in current_criteria:
            operation = client.get_type("AdGroupCriterionOperation")
            operation.remove = resource_name
            operations.append(operation)
        
        # Crear path del ad group
        ad_group_path = f"customers/{customer_id}/adGroups/{ad_group_id}"
        
        # Contadores
        positive_count = 0
        negative_count = 0
        
        # Agregar criterios de género (positivos y negativos)
        gender_enum = client.enums.GenderTypeEnum
        gender_map = {"10": gender_enum.FEMALE, "11": gender_enum.MALE, "20": gender_enum.UNDETERMINED}
        
        for gender_id, state in gender_states.items():
            if str(gender_id) not in gender_map:
                continue
            
            # Solo crear criterios para "included" y "excluded", ignorar "notSet"
            if state == "notSet":
                continue
            
            operation = client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = ad_group_path
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.negative = (state == "excluded")  # "excluded" = negative=True, "included" = negative=False
            criterion.gender.type_ = gender_map[str(gender_id)]
            operations.append(operation)
            
            if state == "included":
                positive_count += 1
            else:
                negative_count += 1
        
        # Agregar criterios de edad (positivos y negativos)
        age_enum = client.enums.AgeRangeTypeEnum
        age_map = {
            "503001": age_enum.AGE_RANGE_18_24,
            "503002": age_enum.AGE_RANGE_25_34,
            "503003": age_enum.AGE_RANGE_35_44,
            "503004": age_enum.AGE_RANGE_45_54,
            "503005": age_enum.AGE_RANGE_55_64,
            "503006": age_enum.AGE_RANGE_65_UP,
            "503999": age_enum.AGE_RANGE_UNDETERMINED
        }
        
        for age_id, state in age_states.items():
            if str(age_id) not in age_map:
                continue
            
            # Solo crear criterios para "included" y "excluded", ignorar "notSet"
            if state == "notSet":
                continue
            
            operation = client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = ad_group_path
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.negative = (state == "excluded")  # "excluded" = negative=True, "included" = negative=False
            criterion.age_range.type_ = age_map[str(age_id)]
            operations.append(operation)
            
            if state == "included":
                positive_count += 1
            else:
                negative_count += 1
        
        # Agregar criterios de ingreso (positivos y negativos)
        income_enum = client.enums.IncomeRangeTypeEnum
        income_map = {
            "31000": income_enum.INCOME_RANGE_0_50,
            "31001": income_enum.INCOME_RANGE_50_60,
            "31002": income_enum.INCOME_RANGE_60_70,
            "31003": income_enum.INCOME_RANGE_70_80,
            "31004": income_enum.INCOME_RANGE_80_90,
            "31005": income_enum.INCOME_RANGE_90_UP,
            "31006": income_enum.INCOME_RANGE_UNDETERMINED
        }
        
        for income_id, state in income_states.items():
            if str(income_id) not in income_map:
                continue
            
            # Solo crear criterios para "included" y "excluded", ignorar "notSet"
            if state == "notSet":
                continue
            
            operation = client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = ad_group_path
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.negative = (state == "excluded")  # "excluded" = negative=True, "included" = negative=False
            criterion.income_range.type_ = income_map[str(income_id)]
            operations.append(operation)
            
            if state == "included":
                positive_count += 1
            else:
                negative_count += 1
        
        # Ejecutar todas las operaciones
        if operations:
            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=operations
            )
            
            updated_count = len(response.results)
        else:
            updated_count = 0
        
        result = jsonify({
            "success": True,
            "message": f"Segmentación demográfica actualizada exitosamente",
            "updatedCount": updated_count,
            "details": {
                "positiveTargeting": positive_count,
                "negativeTargeting": negative_count,
                "totalCriteria": positive_count + negative_count
            }
        })
        
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        error_details = []
        for error in ex.failure.errors:
            error_details.append({
                "message": error.message,
                "error_code": str(error.error_code) if hasattr(error, 'error_code') else None
            })
        
        print(f"❌ GoogleAdsException: {errors}")
        print(f"❌ Request ID: {ex.request_id}")
        print(f"❌ Error details: {error_details}")
        
        result = jsonify({
            "success": False,
            "message": "Error actualizando demografía",
            "errors": errors,
            "error_details": error_details,
            "request_id": ex.request_id
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as ex:
        result = jsonify({
            "success": False,
            "message": str(ex)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/adgroup/create', methods=['POST', 'OPTIONS'])
def create_ad_group():
    """Crea un nuevo grupo de anuncios en una campaña"""
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId')
        campaign_id = data.get('campaignId')
        ad_group_name = data.get('name')
        cpc_bid_micros = data.get('cpcBidMicros')  # En micros (1 USD = 1,000,000 micros)
        
        # Validaciones
        if not all([customer_id, campaign_id, ad_group_name]):
            return jsonify({
                "success": False,
                "message": "Faltan campos requeridos: customerId, campaignId, name"
            }), 400
        
        # Si no se proporciona CPC, usar valor por defecto (1 USD = 1,000,000 micros)
        if not cpc_bid_micros:
            cpc_bid_micros = 1000000
        
        print(f"📝 Creando Ad Group:")
        print(f"   Customer ID: {customer_id}")
        print(f"   Campaign ID: {campaign_id}")
        print(f"   Nombre: {ad_group_name}")
        print(f"   CPC Bid: ${cpc_bid_micros / 1000000:.2f}")
        
        # Crear cliente
        client = get_client_from_request()
        ad_group_service = client.get_service("AdGroupService")
        
        # Crear operación
        ad_group_operation = client.get_type("AdGroupOperation")
        ad_group = ad_group_operation.create
        
        # Configurar ad group
        ad_group.name = ad_group_name
        ad_group.campaign = client.get_service("CampaignService").campaign_path(customer_id, campaign_id)
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ad_group.cpc_bid_micros = int(cpc_bid_micros)
        
        # Ejecutar operación
        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id,
            operations=[ad_group_operation]
        )
        
        # Extraer ID del ad group creado
        ad_group_resource_name = response.results[0].resource_name
        ad_group_id = ad_group_resource_name.split('/')[-1]
        
        print(f"✅ Ad Group creado exitosamente: {ad_group_id}")
        
        result = jsonify({
            "success": True,
            "message": "Ad Group creado exitosamente",
            "adGroupId": ad_group_id,
            "resourceName": ad_group_resource_name
        })
        
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        error_details = []
        
        for error in ex.failure.errors:
            error_details.append({
                "message": error.message,
                "error_code": str(error.error_code) if hasattr(error, 'error_code') else None
            })
        
        print(f"❌ GoogleAdsException creando Ad Group: {errors}")
        print(f"❌ Request ID: {ex.request_id}")
        
        result = jsonify({
            "success": False,
            "message": "Error creando Ad Group",
            "errors": errors,
            "error_details": error_details,
            "request_id": ex.request_id
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as ex:
        print(f"❌ Error inesperado: {str(ex)}")
        result = jsonify({
            "success": False,
            "message": str(ex)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/keywords/add', methods=['POST', 'OPTIONS'])
def add_keywords():
    """Agrega keywords a un grupo de anuncios"""
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId')
        ad_group_id = data.get('adGroupId')
        keywords = data.get('keywords', [])  # Array de objetos: [{text: "keyword", matchType: "BROAD"}]
        
        # Validaciones
        if not all([customer_id, ad_group_id]):
            return jsonify({
                "success": False,
                "message": "Faltan campos requeridos: customerId, adGroupId"
            }), 400
        
        if not keywords or len(keywords) == 0:
            return jsonify({
                "success": False,
                "message": "Debes proporcionar al menos una keyword"
            }), 400
        
        print(f"📝 Agregando {len(keywords)} keywords al Ad Group {ad_group_id}")
        
        # Crear cliente
        client = get_client_from_request()
        ad_group_criterion_service = client.get_service("AdGroupCriterionService")
        ad_group_service = client.get_service("AdGroupService")
        
        operations = []
        
        # Crear operación para cada keyword
        for kw in keywords:
            keyword_text = kw.get('text', '')
            match_type = kw.get('matchType', 'BROAD')  # BROAD, PHRASE, EXACT
            cpc_bid_micros = kw.get('cpcBidMicros')  # Opcional: bid específico para esta keyword
            
            if not keyword_text:
                continue
            
            # Crear operación
            ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
            criterion = ad_group_criterion_operation.create
            
            criterion.ad_group = ad_group_service.ad_group_path(customer_id, ad_group_id)
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.keyword.text = keyword_text
            
            # Match type
            if match_type.upper() == 'BROAD':
                criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            elif match_type.upper() == 'PHRASE':
                criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
            elif match_type.upper() == 'EXACT':
                criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
            else:
                criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            
            # CPC bid específico (opcional)
            if cpc_bid_micros:
                criterion.cpc_bid_micros = int(cpc_bid_micros)
            
            operations.append(ad_group_criterion_operation)
            
            print(f"   - '{keyword_text}' ({match_type})")
        
        if not operations:
            return jsonify({
                "success": False,
                "message": "No se proporcionaron keywords válidas"
            }), 400
        
        # Ejecutar operaciones en batch
        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id,
            operations=operations
        )
        
        # Recopilar IDs de keywords creadas
        keyword_ids = []
        for result in response.results:
            criterion_id = result.resource_name.split('~')[-1]
            keyword_ids.append(criterion_id)
        
        print(f"✅ {len(keyword_ids)} keywords agregadas exitosamente")
        
        result = jsonify({
            "success": True,
            "message": f"{len(keyword_ids)} keywords agregadas exitosamente",
            "keywordsAdded": len(keyword_ids),
            "keywordIds": keyword_ids
        })
        
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        error_details = []
        
        for error in ex.failure.errors:
            error_details.append({
                "message": error.message,
                "error_code": str(error.error_code) if hasattr(error, 'error_code') else None,
                "trigger": error.trigger.string_value if hasattr(error, 'trigger') else None
            })
        
        print(f"❌ GoogleAdsException agregando keywords: {errors}")
        print(f"❌ Request ID: {ex.request_id}")
        
        result = jsonify({
            "success": False,
            "message": "Error agregando keywords",
            "errors": errors,
            "error_details": error_details,
            "request_id": ex.request_id
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as ex:
        print(f"❌ Error inesperado: {str(ex)}")
        result = jsonify({
            "success": False,
            "message": str(ex)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/demographics/stats', methods=['POST', 'OPTIONS'])
def get_demographic_stats():
    """Obtiene estadísticas de conversiones por segmento demográfico
    
    Retorna conversiones por género, edad e ingresos para un ad group y rango de fechas específico.
    """
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId')
        ad_group_id = data.get('adGroupId')
        days = data.get('days', 7)
        
        if not all([customer_id, ad_group_id]):
            result = jsonify({
                "success": False,
                "message": "Faltan customerId o adGroupId"
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        # Crear cliente
        client = get_client_from_request()
        google_ads_service = client.get_service("GoogleAdsService")
        
        # Calcular rango de fechas
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(days))
        date_start = start_date.strftime("%Y-%m-%d")
        date_end = end_date.strftime("%Y-%m-%d")
        
        print(f"📊 [CORRECTED] Loading demographic stats for AdGroup {ad_group_id}, period: {date_start} to {date_end}")
        
        stats = {
            "gender": {},
            "age": {},
            "income": {}
        }
        
        # ===== GÉNERO - Query usando gender_view =====
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
                # resource_name format: customers/X/genderViews/AD_GROUP_ID~CRITERION_ID
                resource_name = row.gender_view.resource_name
                criterion_id = resource_name.split('~')[-1]  # Extraer ID del final
                
                print(f"   🔹 Gender ID {criterion_id}: Conv={row.metrics.conversions}, Clicks={row.metrics.clicks}")
                
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
            
            print(f"✅ Gender stats obtenidas: {len(stats['gender'])} segmentos")
        
        except Exception as e:
            print(f"⚠️ Error loading gender stats: {str(e)}")
            # Llenar con 0s en caso de error
            for gender_id in ["10", "11", "20"]:
                stats["gender"][gender_id] = {
                    "conversions": 0.0,
                    "conversionsValue": 0.0,
                    "clicks": 0.0,
                    "impressions": 0.0,
                    "cost": 0.0,
                    "isNegative": False
                }
        
        # ===== EDAD - Query usando age_range_view =====
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
                # resource_name format: customers/X/ageRangeViews/AD_GROUP_ID~CRITERION_ID
                resource_name = row.age_range_view.resource_name
                criterion_id = resource_name.split('~')[-1]  # Extraer ID del final
                
                print(f"   🔹 Age ID {criterion_id}: Conv={row.metrics.conversions}, Clicks={row.metrics.clicks}")
                
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
            
            print(f"✅ Age stats obtenidas: {len(stats['age'])} segmentos")
        
        except Exception as e:
            print(f"⚠️ Error loading age stats: {str(e)}")
        
        # ===== INGRESO - Query usando income_range_view =====
        try:
            # Mapeo: API devuelve 510xxx pero el modelo Swift espera 31xxx
            income_id_map = {
                "510000": "31006",  # UNDETERMINED -> UNDETERMINED
                "510001": "31005",  # 0-50K
                "510002": "31004",  # 50-60K
                "510003": "31003",  # 60-70K
                "510004": "31002",  # 70-80K
                "510005": "31001",  # 80-UP
                "510006": "31000",  # TOP_10_PERCENT
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
                # resource_name format: customers/X/incomeRangeViews/AD_GROUP_ID~CRITERION_ID
                resource_name = row.income_range_view.resource_name
                api_id = resource_name.split('~')[-1]  # Extraer ID de la API (510xxx)
                criterion_id = income_id_map.get(api_id, api_id)  # Mapear a 31xxx
                
                print(f"   🔹 Income API_ID {api_id} -> {criterion_id}: Conv={row.metrics.conversions}, Clicks={row.metrics.clicks}")
                
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
            
            print(f"✅ Income stats obtenidas: {len(stats['income'])} segmentos")
        
        except Exception as e:
            print(f"⚠️ Error loading income stats: {str(e)}")
        
        print(f"✅ [CORRECTED] Stats loaded: {len(stats['gender'])} gender, {len(stats['age'])} age, {len(stats['income'])} income")
        
        result = jsonify({
            "success": True,
            "stats": stats,
            "dateRange": {
                "start": date_start,
                "end": date_end,
                "days": days
            }
        })
        
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        errors = []
        error_details = []
        
        for error in ex.failure.errors:
            error_string = f'Error code: {error.error_code} | Message: {error.message}'
            errors.append(error_string)
            error_details.append({
                'error_code': str(error.error_code),
                'message': error.message
            })
        
        print(f"❌ GoogleAdsException obteniendo demographic stats: {errors}")
        
        result = jsonify({
            "success": False,
            "message": "Error obteniendo estadísticas demográficas",
            "errors": errors,
            "error_details": error_details
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as ex:
        print(f"❌ Error inesperado: {str(ex)}")
        result = jsonify({
            "success": False,
            "message": str(ex)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result


# ==========================================
# AGREGAR ESTE ENDPOINT AL FINAL DE app.py

# ==========================================
# CIRCUIT BREAKER - Budget Protection System
# ==========================================
app.register_blueprint(circuit_breaker_bp)
start_circuit_breaker_scheduler()


# ==========================================
# (Antes de "if __name__ == '__main__':")
# ==========================================

@app.route('/api/analytics/campaign', methods=['POST', 'OPTIONS'])
def get_campaign_analytics():
    """
    Obtiene analytics completo de una campaña
    
    Request Body:
    {
        "customer_id": "1234567890",
        "campaign_id": "9876543210",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31"
    }
    """
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # Obtener datos del request
        data = request.get_json()
        customer_id = data.get('customer_id')
        campaign_id = data.get('campaign_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Validar
        if not all([customer_id, campaign_id, start_date, end_date]):
            result = jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos',
                'required': ['customer_id', 'campaign_id', 'start_date', 'end_date']
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        # Crear cliente
        client = get_client_from_request()
        ga_service = client.get_service("GoogleAdsService")
        
        # Limpiar customer_id
        customer_id = customer_id.replace('-', '')
        
        print(f"📊 Fetching analytics for campaign {campaign_id}")
        
        # 1. Obtener keywords
        keywords_query = f"""
            SELECT
              ad_group.id,
              ad_group_criterion.criterion_id,
              ad_group_criterion.keyword.text,
              ad_group_criterion.keyword.match_type,
              ad_group_criterion.quality_info.quality_score,
              metrics.impressions,
              metrics.clicks,
              metrics.conversions,
              metrics.cost_micros,
              metrics.ctr,
              metrics.conversions_from_interactions_rate
            FROM keyword_view
            WHERE campaign.id = '{campaign_id}'
              AND segments.date BETWEEN '{start_date}' AND '{end_date}'
              AND ad_group_criterion.status = 'ENABLED'
            ORDER BY metrics.impressions DESC
            LIMIT 100
        """
        
        keywords_response = ga_service.search(
            customer_id=customer_id,
            query=keywords_query
        )
        
        keywords = []
        for row in keywords_response:
            criterion = row.ad_group_criterion
            metrics = row.metrics
            
            keywords.append({
                'id': str(criterion.criterion_id),
                'ad_group_id': str(row.ad_group.id),
                'keyword': criterion.keyword.text,
                'match_type': criterion.keyword.match_type.name,
                'quality_score': criterion.quality_info.quality_score if criterion.quality_info else None,
                'impressions': int(metrics.impressions),
                'clicks': int(metrics.clicks),
                'conversions': float(metrics.conversions),
                'cost': float(metrics.cost_micros) / 1_000_000,
                'ctr': float(metrics.ctr) * 100,
                'conversion_rate': float(metrics.conversions_from_interactions_rate) * 100
            })
        
        print(f"✅ Found {len(keywords)} keywords")
        
        # 2. Obtener ads
        ads_query = f"""
            SELECT
              ad_group.id,
              ad_group_ad.ad.id,
              ad_group.name,
              ad_group_ad.ad.responsive_search_ad.headlines,
              ad_group_ad.status,
              metrics.impressions,
              metrics.clicks,
              metrics.conversions,
              metrics.cost_micros,
              metrics.ctr,
              metrics.conversions_from_interactions_rate
            FROM ad_group_ad
            WHERE campaign.id = '{campaign_id}'
              AND segments.date BETWEEN '{start_date}' AND '{end_date}'
              AND ad_group_ad.status = 'ENABLED'
            ORDER BY metrics.impressions DESC
            LIMIT 50
        """
        
        ads_response = ga_service.search(
            customer_id=customer_id,
            query=ads_query
        )
        
        ads = []
        for row in ads_response:
            ad = row.ad_group_ad.ad
            ad_group = row.ad_group
            metrics = row.metrics
            
            # Extraer headlines
            headlines = []
            if ad.responsive_search_ad and ad.responsive_search_ad.headlines:
                headlines = [h.text for h in ad.responsive_search_ad.headlines]
            
            ads.append({
                'id': str(ad.id),
                'ad_group_id': str(ad_group.id),
                'ad_group_name': ad_group.name,
                'headlines': headlines,
                'status': row.ad_group_ad.status.name,
                'impressions': int(metrics.impressions),
                'clicks': int(metrics.clicks),
                'conversions': float(metrics.conversions),
                'cost': float(metrics.cost_micros) / 1_000_000,
                'ctr': float(metrics.ctr) * 100,
                'conversion_rate': float(metrics.conversions_from_interactions_rate) * 100
            })
        
        print(f"✅ Found {len(ads)} ads")
        
        # 3. Obtener hourly performance
        hourly_query = f"""
            SELECT
              segments.hour,
              metrics.impressions,
              metrics.clicks,
              metrics.conversions,
              metrics.cost_micros,
              metrics.ctr
            FROM campaign
            WHERE campaign.id = '{campaign_id}'
              AND segments.date BETWEEN '{start_date}' AND '{end_date}'
        """
        
        hourly_response = ga_service.search(
            customer_id=customer_id,
            query=hourly_query
        )
        
        # Agregar por hora
        hourly_data = {}
        for row in hourly_response:
            hour = row.segments.hour
            metrics = row.metrics
            
            if hour not in hourly_data:
                hourly_data[hour] = {
                    'impressions': 0,
                    'clicks': 0,
                    'conversions': 0,
                    'cost': 0
                }
            
            hourly_data[hour]['impressions'] += int(metrics.impressions)
            hourly_data[hour]['clicks'] += int(metrics.clicks)
            hourly_data[hour]['conversions'] += float(metrics.conversions)
            hourly_data[hour]['cost'] += float(metrics.cost_micros) / 1_000_000
        
        # Convertir a lista
        hourly_performance = []
        for hour in range(24):
            data = hourly_data.get(hour, {'impressions': 0, 'clicks': 0, 'conversions': 0, 'cost': 0})
            ctr = (data['clicks'] / data['impressions'] * 100) if data['impressions'] > 0 else 0
            
            hourly_performance.append({
                'hour': hour,
                'impressions': data['impressions'],
                'clicks': data['clicks'],
                'conversions': data['conversions'],
                'cost': data['cost'],
                'ctr': ctr
            })
        
        print(f"✅ Generated hourly performance data")
        
        # Obtener nombre de campaña
        campaign_query = f"""
            SELECT campaign.id, campaign.name
            FROM campaign
            WHERE campaign.id = '{campaign_id}'
        """
        
        campaign_response = ga_service.search(
            customer_id=customer_id,
            query=campaign_query
        )
        
        campaign_name = "Unknown Campaign"
        for row in campaign_response:
            campaign_name = row.campaign.name
            break
        
        # Respuesta completa
        result = jsonify({
            'success': True,
            'campaign_name': campaign_name,
            'date_range': f"{start_date} to {end_date}",
            'keywords': keywords,
            'ads': ads,
            'hourly_performance': hourly_performance
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        error_message = f"Google Ads API Error: {ex.error.code().name}"
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': error_message,
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result




# ==========================================
# ENDPOINTS DE ACCIONES: PAUSAR KEYWORDS Y ADS
# ==========================================

@app.route('/api/keyword/pause', methods=['POST', 'OPTIONS'])
def pause_keyword():
    """
    Pausa una keyword específica
    
    Request Body:
    {
        "customer_id": "1234567890",
        "ad_group_id": "9876543210",
        "criterion_id": "12345678901234"
    }
    """
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        ad_group_id = data.get('ad_group_id')
        criterion_id = data.get('criterion_id')
        
        if not all([customer_id, ad_group_id, criterion_id]):
            result = jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos',
                'required': ['customer_id', 'ad_group_id', 'criterion_id']
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        # Crear cliente
        client = get_client_from_request()
        ad_group_criterion_service = client.get_service("AdGroupCriterionService")
        
        # Limpiar customer_id
        customer_id = customer_id.replace('-', '')
        
        # Crear resource name
        resource_name = ad_group_criterion_service.ad_group_criterion_path(
            customer_id,
            ad_group_id,
            criterion_id
        )
        
        print(f"⏸️  Pausing keyword: {resource_name}")
        
        # Crear operación de actualización
        ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
        ad_group_criterion = ad_group_criterion_operation.update
        ad_group_criterion.resource_name = resource_name
        ad_group_criterion.status = client.enums.AdGroupCriterionStatusEnum.PAUSED
        
        # Field mask - solo especificar el campo que cambia
        ad_group_criterion_operation.update_mask.CopyFrom(
            FieldMask(paths=["status"])
        )
        
        # Ejecutar
        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id,
            operations=[ad_group_criterion_operation]
        )
        
        print(f"✅ Keyword paused successfully")
        
        result = jsonify({
            'success': True,
            'message': 'Keyword pausada exitosamente',
            'resource_name': response.results[0].resource_name
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        error_message = f"Google Ads API Error: {ex.error.code().name}"
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': error_message,
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
    return result


# Assets

def link_asset_to_context(ga_client, customer_id, asset_resource_name, field_type_enum_value, campaign_id, ad_group_id=None):
    if ad_group_id:
        svc = ga_client.get_service("AdGroupAssetService")
        op = ga_client.get_type("AdGroupAssetOperation")
        create = op.create
        create.ad_group = f"customers/{customer_id}/adGroups/{ad_group_id}"
        create.asset = asset_resource_name
        create.field_type = field_type_enum_value
        svc.mutate_ad_group_assets(customer_id=customer_id, operations=[op])
    elif campaign_id:
        svc = ga_client.get_service("CampaignAssetService")
        op = ga_client.get_type("CampaignAssetOperation")
        create = op.create
        create.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
        create.asset = asset_resource_name
        create.field_type = field_type_enum_value
        svc.mutate_campaign_assets(customer_id=customer_id, operations=[op])
    else:
        svc = ga_client.get_service("CustomerAssetService")
        op = ga_client.get_type("CustomerAssetOperation")
        create = op.create
        create.customer = f"customers/{customer_id}"
        create.asset = asset_resource_name
        create.field_type = field_type_enum_value
        svc.mutate_customer_assets(customer_id=customer_id, operations=[op])

def cors_preflight_ok():
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    return response

@app.route('/api/assets/create-image', methods=['POST', 'OPTIONS'])
def create_image_asset():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        campaign_id = data.get('campaignId')
        ad_group_id = data.get('adGroupId')
        fmt = data.get('format')
        image_b64 = data.get('imageBase64')
        if not all([customer_id, fmt, image_b64]):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        raw = base64.b64decode(image_b64)
        if len(raw) > 5 * 1024 * 1024:
            return jsonify({"success": False, "policyViolation": "Imagen supera 5MB"}), 400
        img = Image.open(BytesIO(raw))
        w, h = img.size
        if fmt == 'MARKETING':
            ratio = w / max(h, 1)
            if not (w >= 600 and h >= 314 and abs(ratio - 1.91) < 0.15):
                return jsonify({"success": False, "policyViolation": "Dimensiones/ratio inválidas para Marketing"}), 400
        elif fmt == 'SQUARE':
            if not (w >= 300 and h >= 300 and abs(w - h) < 5):
                return jsonify({"success": False, "policyViolation": "Dimensiones inválidas para Square"}), 400
        ga = get_client_from_request()
        svc = ga.get_service("AssetService")
        op = ga.get_type("AssetOperation")
        asset = op.create
        asset.name = "Image Asset"
        asset.image_asset.data = raw
        resp = svc.mutate_assets(customer_id=customer_id, operations=[op])
        res_name = resp.results[0].resource_name
        field_enum = ga.get_type("AssetFieldTypeEnum").AssetFieldType.IMAGE
        link_asset_to_context(ga, customer_id, res_name, field_enum, campaign_id, ad_group_id)
        result = jsonify({"success": True, "resourceName": res_name})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = []
        details = []
        for error in ex.failure.errors:
            errors.append(error.message)
            path = []
            if error.location and error.location.field_path_elements:
                for fpe in error.location.field_path_elements:
                    path.append(getattr(fpe, 'field_name', ''))
            details.append({
                'message': error.message,
                'code': ex.error.code().name if hasattr(ex, 'error') else 'UNKNOWN',
                'path': path
            })
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors, "details": details})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/campaigns/top-final-urls', methods=['POST', 'OPTIONS'])
def top_campaign_final_urls():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        if not customer_id:
            res = jsonify({"success": False, "message": "customerId requerido"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_client_from_request()
        service = ga.get_service('GoogleAdsService')
        query = (
            "SELECT campaign.id, campaign.name, campaign.status, campaign_budget.amount_micros "
            "FROM campaign WHERE campaign.status = 'ENABLED' ORDER BY campaign_budget.amount_micros DESC LIMIT 1"
        )
        rows = service.search(customer_id=customer_id, query=query)
        top_campaign_id = None
        for row in rows:
            top_campaign_id = row.campaign.id
            break
        if not top_campaign_id:
            result = jsonify({"success": True, "finalUrls": []})
            result.headers.add('Access-Control-Allow-Origin', '*')
            return result
        query_urls = (
            "SELECT ad_group_ad.ad.final_urls FROM ad_group_ad "
            f"WHERE campaign.id = '{top_campaign_id}' AND ad_group_ad.status = 'ENABLED'"
        )
        url_rows = service.search(customer_id=customer_id, query=query_urls)
        urls = []
        for row in url_rows:
            if row.ad_group_ad.ad.final_urls:
                urls.extend(list(row.ad_group_ad.ad.final_urls))
        urls = list(dict.fromkeys(urls))
        result = jsonify({"success": True, "campaignId": str(top_campaign_id), "finalUrls": urls})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/sitelinks/generate', methods=['POST', 'OPTIONS'])
def generate_sitelinks():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        keywords_raw = data.get('keywords', '')
        count = int(data.get('count', 4))
        provider = (data.get('provider') or 'deepseek').lower()
        if not customer_id:
            res = jsonify({"success": False, "message": "customerId requerido"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_client_from_request()
        service = ga.get_service('GoogleAdsService')
        query = (
            "SELECT campaign.id, campaign.name, campaign.status, campaign_budget.amount_micros "
            "FROM campaign WHERE campaign.status = 'ENABLED' ORDER BY campaign_budget.amount_micros DESC LIMIT 1"
        )
        rows = service.search(customer_id=customer_id, query=query)
        top_campaign_id = None
        for row in rows:
            top_campaign_id = row.campaign.id
            break
        base_url = None
        if top_campaign_id:
            query_urls = (
                "SELECT ad_group_ad.ad.final_urls FROM ad_group_ad "
                f"WHERE campaign.id = '{top_campaign_id}' AND ad_group_ad.status = 'ENABLED'"
            )
            url_rows = service.search(customer_id=customer_id, query=query_urls)
            for row in url_rows:
                if row.ad_group_ad.ad.final_urls:
                    base_url = list(row.ad_group_ad.ad.final_urls)[0]
                    break
        seeds = [s.strip() for s in keywords_raw.split(',') if s.strip()]
        if not seeds:
            seeds = ['promo']
        def slugify(s):
            return ''.join(ch for ch in s.lower() if ch.isalnum() or ch == ' ').replace(' ', '')
        def clamp(s, n):
            return s[:n]
        sitelinks = []
        prompt = (
            "You are an expert Google Ads copywriter. Given keywords, generate N sitelinks as JSON array. "
            "Each item must strictly follow: title<=25 chars, description1<=35, description2<=35. "
            "Use persuasive Spanish copy. Reply ONLY with JSON. Schema: [{\"title\",\"description1\",\"description2\"}]. "
            f"keywords: {', '.join(seeds)}; N: {count}."
        )
        def extract_json(text):
            if not text:
                return None
            # strip code fences
            t = text.strip()
            t = t.replace('```json', '').replace('```', '')
            # find first [ and last ] to isolate array
            start = t.find('[')
            end = t.rfind(']')
            if start != -1 and end != -1 and end > start:
                t = t[start:end+1]
            # normalize quotes
            t = t.replace('\u201c', '"').replace('\u201d', '"').replace('“', '"').replace('”', '"')
            try:
                return json.loads(t)
            except:
                return None

        last_error = None
        last_status = None

        def use_openai(p):
            key = os.environ.get('OPENAI_API_KEY')
            if not key:
                return None
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            body = {
                "model": os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
                "messages": [{"role": "user", "content": p}],
                "temperature": 0.8
            }
            r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(body), timeout=30)
            if r.status_code != 200:
                last_status = r.status_code
                last_error = r.text[:500]
                return None
            content = r.json().get('choices',[{}])[0].get('message',{}).get('content','[]')
            return extract_json(content)
        def use_gemini(p):
            key = os.environ.get('GOOGLE_API_KEY')
            if not key:
                return None
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            body = {"contents": [{"parts": [{"text": p}]}]}
            r = requests.post(url, json=body, timeout=30)
            if r.status_code != 200:
                last_status = r.status_code
                last_error = r.text[:500]
                return None
            parts = r.json().get('candidates',[{}])[0].get('content',{}).get('parts',[{}])
            text = parts[0].get('text','[]')
            return extract_json(text)
        def use_deepseek(p):
            key = os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPEN_ROUTER_API_KEY')
            if not key:
                return None
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            body = {
                "model": os.environ.get('DEEPSEEK_MODEL','deepseek-chat'),
                "messages": [{"role":"user","content": p}],
                "temperature": 0.8
            }
            r = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, data=json.dumps(body), timeout=30)
            if r.status_code != 200:
                last_status = r.status_code
                last_error = r.text[:500]
                return None
            content = r.json().get('choices',[{}])[0].get('message',{}).get('content','[]')
            return extract_json(content)
        candidates = None
        if provider == 'openai':
            candidates = use_openai(prompt)
            if candidates is None:
                candidates = use_gemini(prompt)
        elif provider == 'gemini':
            candidates = use_gemini(prompt)
            if candidates is None:
                candidates = use_openai(prompt)
        else:
            candidates = use_deepseek(prompt)
            if candidates is None:
                candidates = use_openai(prompt)
        if not isinstance(candidates, list):
            candidates = []
        if not candidates:
            detail = {
                "provider": provider,
                "status": last_status,
                "error": last_error,
                "configured": {
                    "openai": bool(os.environ.get('OPENAI_API_KEY')),
                    "gemini": bool(os.environ.get('GOOGLE_API_KEY')),
                    "deepseek": bool(os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPEN_ROUTER_API_KEY'))
                }
            }
            res = jsonify({"success": False, "message": "AI provider response unavailable", "details": detail})
            res.status_code = 500
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        for i in range(min(count, len(candidates))):
            item = candidates[i]
            title = clamp(str(item.get('title','')).strip(), 25)
            d1 = clamp(str(item.get('description1','')).strip(), 35)
            d2 = clamp(str(item.get('description2','')).strip(), 35)
            base = base_url or 'https://example.com'
            url = base.split('#')[0] + '#' + slugify(title)
            sitelinks.append({"title": title, "description1": d1, "description2": d2, "url": url})
        result = jsonify({"success": True, "sitelinks": sitelinks})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/assets/summary', methods=['POST', 'OPTIONS'])
def assets_summary():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        campaign_id = data.get('campaignId')
        ad_group_id = data.get('adGroupId')
        if not all([customer_id, campaign_id]):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_client_from_request()
        service = ga.get_service('GoogleAdsService')

        def list_linked_assets(query, is_campaign=True):
            rows = service.search(customer_id=customer_id, query=query)
            out = []
            for r in rows:
                if is_campaign:
                    out.append((str(r.campaign_asset.asset), r.campaign_asset.field_type.name))
                else:
                    out.append((str(r.ad_group_asset.asset), r.ad_group_asset.field_type.name))
            return out

        camp_query = (
            f"SELECT campaign.id, campaign_asset.asset, campaign_asset.field_type FROM campaign_asset "
            f"WHERE campaign.id = '{campaign_id}' AND campaign_asset.status = 'ENABLED'"
        )
        camp_assets = list_linked_assets(camp_query, is_campaign=True)
        adg_assets = []
        if ad_group_id:
            adg_query = (
                f"SELECT ad_group.id, ad_group_asset.asset, ad_group_asset.field_type FROM ad_group_asset "
                f"WHERE ad_group.id = '{ad_group_id}' AND ad_group_asset.status = 'ENABLED'"
            )
            adg_assets = list_linked_assets(adg_query, is_campaign=False)
        linked = []
        seen = set()
        for rn, ft in camp_assets + adg_assets:
            if rn not in seen:
                seen.add(rn)
                linked.append((rn, ft))

        def get_asset_fields(res_name):
            q = f"SELECT asset.resource_name, asset.sitelink_asset.link_text, asset.callout_asset.callout_text, asset.call_asset.country_code, asset.call_asset.phone_number, asset.promotion_asset.promotion_target, asset.promotion_asset.percent_off, asset.promotion_asset.money_amount_off.amount_micros FROM asset WHERE asset.resource_name = '{res_name}'"
            rows = service.search(customer_id=customer_id, query=q)
            out = {}
            for r in rows:
                out['resource_name'] = r.asset.resource_name
                if r.asset.sitelink_asset and r.asset.sitelink_asset.link_text:
                    out['type'] = 'SITELINK'
                    out['text'] = r.asset.sitelink_asset.link_text
                if r.asset.callout_asset and r.asset.callout_asset.callout_text:
                    out['type'] = 'CALLOUT'
                    out['text'] = r.asset.callout_asset.callout_text
                if r.asset.call_asset and r.asset.call_asset.phone_number:
                    out['type'] = 'CALL'
                    out['phone'] = r.asset.call_asset.phone_number
                if r.asset.promotion_asset and (r.asset.promotion_asset.promotion_target or r.asset.promotion_asset.percent_off):
                    out['type'] = 'PROMOTION'
                    out['event'] = r.asset.promotion_asset.promotion_target
                    out['percent'] = r.asset.promotion_asset.percent_off
                    out['amount_micros'] = r.asset.promotion_asset.money_amount_off.amount_micros if r.asset.promotion_asset.money_amount_off else None
            return out

        sitelinks = []
        callouts = []
        calls = []
        promotions = []
        for rn, ft in linked:
            fields = get_asset_fields(rn)
            t = fields.get('type')
            if t == 'SITELINK' and fields.get('text'):
                sitelinks.append({'text': fields.get('text'), 'resourceName': fields.get('resource_name')})
            elif t == 'CALLOUT' and fields.get('text'):
                callouts.append({'text': fields.get('text'), 'resourceName': fields.get('resource_name')})
            elif t == 'CALL' and fields.get('phone'):
                calls.append({'phone': fields.get('phone'), 'resourceName': fields.get('resource_name')})
            elif t == 'PROMOTION':
                promotions.append({'event': fields.get('event'), 'percent': fields.get('percent'), 'resourceName': fields.get('resource_name')})

        result = jsonify({
            "success": True,
            "sitelinks": sitelinks,
            "callouts": callouts,
            "calls": calls,
            "promotions": promotions
        })
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
@app.route('/api/assets/create-sitelink', methods=['POST', 'OPTIONS'])
def create_sitelink_asset():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        campaign_id = data.get('campaignId')
        ad_group_id = data.get('adGroupId')
        text = data.get('text', '')
        d1 = data.get('description1', '')
        d2 = data.get('description2', '')
        final_url = data.get('finalUrl', '')
        if not all([customer_id, text, final_url]):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        if len(text) > 25 or len(d1) > 35 or len(d2) > 35:
            return jsonify({"success": False, "policyViolation": "Longitudes excedidas"}), 400
        def _slugify(s):
            t = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
            t = ''.join(ch for ch in t.lower() if ch.isalnum())
            return t
        def _normalize_url(u):
            u = (u or '').strip().strip('`').strip('"').strip("'")
            base = u.split('#')[0]
            frag = ''
            if '#' in u:
                frag = u.split('#', 1)[1]
            frag = frag.lstrip('/').strip()
            if frag:
                frag = _slugify(frag)
                # ensure '/#' pattern
                base_no_slash = base.rstrip('/')
                return base_no_slash + '/#' + frag
            return base.rstrip('/')
        final_url = _normalize_url(final_url)
        ga = get_client_from_request()
        svc = ga.get_service("AssetService")
        op = ga.get_type("AssetOperation")
        asset = op.create
        asset.sitelink_asset.link_text = text
        if d1:
            asset.sitelink_asset.description1 = d1
        if d2:
            asset.sitelink_asset.description2 = d2
        # Final URL es requerida por Google Ads para SitelinkAsset; colocar en ambos campos por compatibilidad
        # Final URL debe establecerse en el asset (no dentro de sitelink_asset)
        asset.final_urls.append(final_url)
        print(f"[create-sitelink] customer={customer_id} campaign={campaign_id} adGroup={ad_group_id} text='{text}' url='{final_url}'")
        resp = svc.mutate_assets(customer_id=customer_id, operations=[op])
        res_name = resp.results[0].resource_name
        field_enum = ga.get_type("AssetFieldTypeEnum").AssetFieldType.SITELINK
        link_asset_to_context(ga, customer_id, res_name, field_enum, campaign_id, ad_group_id)
        result = jsonify({"success": True, "resourceName": res_name})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = []
        details = []
        for error in ex.failure.errors:
            errors.append(error.message)
            path = []
            if error.location and error.location.field_path_elements:
                for fpe in error.location.field_path_elements:
                    path.append(getattr(fpe, 'field_name', ''))
            details.append({
                'message': error.message,
                'code': ex.error.code().name if hasattr(ex, 'error') else 'UNKNOWN',
                'path': path
            })
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors, "details": details})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/assets/create-promotion', methods=['POST', 'OPTIONS'])
def create_promotion_asset():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        campaign_id = data.get('campaignId')
        ad_group_id = data.get('adGroupId')
        p = data.get('promotion', {})
        final_url = (data.get('finalUrl', '') or '').strip().strip('`').strip('"').strip("'")
        if not customer_id or not p:
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_client_from_request()
        svc = ga.get_service("AssetService")
        op = ga.get_type("AssetOperation")
        asset = op.create
        if p.get('event'): asset.promotion_asset.promotion_target = p.get('event')
        if p.get('language'): asset.promotion_asset.language_code = p.get('language')
        dt = p.get('discountType')
        if dt == 'percent':
            asset.promotion_asset.percent_off = int(p.get('percent', 0))
        else:
            money = ga.get_type("Money")
            money.currency_code = p.get('currency', 'USD')
            money.amount_micros = int(float(p.get('amount', 0)) * 1_000_000)
            asset.promotion_asset.money_amount_off = money
        if p.get('startDate'): asset.promotion_asset.start_date = p.get('startDate').split('T')[0]
        if p.get('endDate'): asset.promotion_asset.end_date = p.get('endDate').split('T')[0]
        if final_url:
            asset.final_urls.append(final_url)
        resp = svc.mutate_assets(customer_id=customer_id, operations=[op])
        res_name = resp.results[0].resource_name
        field_enum = ga.get_type("AssetFieldTypeEnum").AssetFieldType.PROMOTION
        link_asset_to_context(ga, customer_id, res_name, field_enum, campaign_id, ad_group_id)
        result = jsonify({"success": True, "resourceName": res_name})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

# Lead Form creation removed per product decision

# Price Asset creation removed per product decision

@app.route('/api/assets/create-call', methods=['POST', 'OPTIONS'])
def create_call_asset():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        campaign_id = data.get('campaignId')
        ad_group_id = data.get('adGroupId')
        cc_raw = data.get('countryCode', '')
        phone = data.get('phoneNumber', '')
        code_map = {
            '+52':'MX','52':'MX',
            '+57':'CO','57':'CO',
            '+1':'US','1':'US'
        }
        cc = code_map.get(cc_raw, cc_raw if len(cc_raw)==2 else '')
        if not all([customer_id, cc, phone]):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_client_from_request()
        svc = ga.get_service("AssetService")
        op = ga.get_type("AssetOperation")
        asset = op.create
        asset.call_asset.country_code = cc
        asset.call_asset.phone_number = phone
        resp = svc.mutate_assets(customer_id=customer_id, operations=[op])
        res_name = resp.results[0].resource_name
        field_enum = ga.get_type("AssetFieldTypeEnum").AssetFieldType.CALL
        link_asset_to_context(ga, customer_id, res_name, field_enum, campaign_id, ad_group_id)
        result = jsonify({"success": True, "resourceName": res_name})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/assets/create-callout', methods=['POST', 'OPTIONS'])
def create_callout_asset():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        campaign_id = data.get('campaignId')
        ad_group_id = data.get('adGroupId')
        text = data.get('text')
        texts = data.get('texts') if isinstance(data.get('texts'), list) else None
        if not customer_id or (not text and not texts):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_client_from_request()
        svc = ga.get_service("AssetService")
        operations = []
        items = texts if texts else [text]
        for t in items:
            if not t: 
                continue
            op = ga.get_type("AssetOperation")
            asset = op.create
            asset.callout_asset.callout_text = str(t)[:25]
            operations.append(op)
        resp = svc.mutate_assets(customer_id=customer_id, operations=operations)
        created = [r.resource_name for r in resp.results]
        field_enum = ga.get_type("AssetFieldTypeEnum").AssetFieldType.CALLOUT
        for res_name in created:
            link_asset_to_context(ga, customer_id, res_name, field_enum, campaign_id, ad_group_id)
        result = jsonify({"success": True, "resourceName": created[-1] if created else "", "created": created})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/optimization/analyze-relevance', methods=['POST', 'OPTIONS'])
def analyze_relevance():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        lookback = int(data.get('lookbackWindow', 30))
        if not customer_id:
            res = jsonify({"success": False, "message": "customerId requerido"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback)
        ga = get_client_from_request()
        service = ga.get_service('GoogleAdsService')
        query = (
            "SELECT search_term_view.search_term, metrics.conversions, metrics.clicks, metrics.impressions, "
            "metrics.ctr, metrics.cost_micros, ad_group.id, ad_group.name, campaign.id "
            "FROM search_term_view "
            f"WHERE segments.date >= '{start_date.isoformat()}' AND segments.date <= '{end_date.isoformat()}' "
            "AND metrics.conversions > 0"
        )
        rows = service.search(customer_id=customer_id, query=query)
        
        # Recopilar todos los ad_group_ids únicos para obtener sus URLs
        ad_group_ids = set()
        opportunities_temp = []
        for r in rows:
            clicks = r.metrics.clicks
            impressions = r.metrics.impressions
            conversions = r.metrics.conversions
            ctr = r.metrics.ctr
            cost_micros = r.metrics.cost_micros
            cpa_micros = int(cost_micros / conversions) if conversions > 0 else 0
            low_ctr = ctr < 0.02
            high_cpa = cpa_micros > 5_000_000
            if low_ctr or high_cpa:
                ad_group_id = str(r.ad_group.id)
                ad_group_ids.add(ad_group_id)
                opportunities_temp.append({
                    "searchTerm": r.search_term_view.search_term,
                    "conversions": float(conversions),
                    "clicks": int(clicks),
                    "impressions": int(impressions),
                    "ctr": float(ctr),
                    "cpaMicros": int(cpa_micros),
                    "costMicros": int(cost_micros),
                    "adGroupId": ad_group_id,
                    "adGroupName": r.ad_group.name,
                    "campaignId": str(r.campaign.id),
                    "potentialSavingsMicros": int(cost_micros * 0.1)
                })
        
        # Obtener URLs de los anuncios de cada ad group
        ad_group_urls = {}
        if ad_group_ids:
            ad_groups_filter = " OR ".join([f"ad_group.id = '{ag_id}'" for ag_id in ad_group_ids])
            ads_query = (
                "SELECT ad_group.id, ad_group_ad.ad.final_urls "
                "FROM ad_group_ad "
                f"WHERE ({ad_groups_filter}) "
                "AND ad_group_ad.status = 'ENABLED' "
                "LIMIT 1000"
            )
            try:
                ads_rows = service.search(customer_id=customer_id, query=ads_query)
                for ad_row in ads_rows:
                    ag_id = str(ad_row.ad_group.id)
                    if ad_row.ad_group_ad.ad.final_urls and len(ad_row.ad_group_ad.ad.final_urls) > 0:
                        # Tomar la primera URL disponible
                        if ag_id not in ad_group_urls:
                            ad_group_urls[ag_id] = ad_row.ad_group_ad.ad.final_urls[0]
            except Exception as url_ex:
                print(f"⚠️ Error obteniendo URLs: {url_ex}")
        
        # Agregar URLs a las oportunidades
        opportunities = []
        for opp in opportunities_temp:
            opp["finalUrl"] = ad_group_urls.get(opp["adGroupId"], "")
            opportunities.append(opp)
        result = jsonify({"success": True, "opportunities": opportunities})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/optimization/generate-adcopy', methods=['POST', 'OPTIONS'])
def generate_adcopy():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        term = str(data.get('searchTerm','')).strip()
        provider = (data.get('provider') or 'deepseek').lower()
        if not term:
            res = jsonify({"success": False, "message": "searchTerm requerido"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        def extract_json(text):
            if not text:
                return None
            t = text.strip().replace('```json', '').replace('```', '')
            start = t.find('{')
            end = t.rfind('}')
            if start != -1 and end != -1 and end > start:
                t = t[start:end+1]
            t = t.replace('\u201c', '"').replace('\u201d', '"').replace('“', '"').replace('”', '"')
            try:
                return json.loads(t)
            except:
                return None
        def clamp(s, n):
            return (s or '')[:n]

        def normalize_snippet(text: str, limit: int) -> str:
            if not text:
                return ''
            # Consolidate whitespace and trim ends
            stripped = ' '.join(str(text).split())
            if len(stripped) <= limit:
                return stripped
            truncated = stripped[:limit].rstrip()
            # Avoid cutting words in half when possible
            if len(stripped) > limit and not stripped[limit].isspace():
                last_space = truncated.rfind(' ')
                if last_space > 10:  # keep at least a short prefix
                    truncated = truncated[:last_space]
            return truncated.strip()
        prompt = (
            "ACTÚA COMO: Copywriter experto en Google Ads (Direct Response) especializado en SKAGs de alto CTR.\n"
            f"TAREA: Genera un objeto JSON crudo con 15 'headlines' y 4 'descriptions' para el término de búsqueda: '{term}'.\n\n"
            
            "--- REGLAS CRÍTICAS (NO ROMPER) ---\n"
            "1. LONGITUD HEADLINES: MÁXIMO 30 caracteres. Si te pasas, el anuncio será rechazado. Sé conciso.\n"
            "2. LONGITUD DESCRIPTIONS: MÁXIMO 90 caracteres.\n"
            "3. INTEGRIDAD: NUNCA cortes palabras a la mitad (ej: NO 'Amar', 'Gar', 'Por'). Si no cabe, reescribe la frase.\n"
            "4. GRAMÁTICA: No termines con preposiciones sueltas ('de', 'en', 'y', 'con'). La frase debe tener sentido completo.\n"
            "5. FORMATO: Usa 'Title Case' (Primera Letra Mayúscula) para mayor impacto visual.\n\n"
            
            "--- ESTRATEGIA DE CONTENIDO ---\n"
            "1. INSERCIÓN DE KEYWORD: El término (o su abreviación lógica) DEBE aparecer:\n"
            "   - Mínimo 6 veces en los headlines.\n"
            "   - Mínimo 3 veces en las descriptions.\n"
            "2. ABREVIACIÓN INTELIGENTE: Si el término es largo (>25 chars), abrévialo naturalmente.\n"
            "   - 'amarres de amor cerca de mi' -> 'Amarres Amor Cerca' (BIEN)\n"
            "   - 'amarres de amor cerca de mi' -> 'Amarres De Amor Cer' (MAL)\n"
            "3. ÁNGULOS DE VENTA: Mezcla urgencia, beneficios, autoridad y localidad.\n\n"
            
            "--- FORMATO DE RESPUESTA ---\n"
            "Responde SOLO con el JSON válido. NO uses bloques de código markdown (```json). \n"
            "Estructura: {\"headlines\": [...], \"descriptions\": [...]}\n"
            f"TÉRMINO OBJETIVO: {term}"
        )
        def use_openai(p):
            key = os.environ.get('OPENAI_API_KEY')
            if not key:
                return None
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            body = {"model": os.environ.get('OPENAI_MODEL','gpt-4o-mini'), "messages": [{"role":"user","content": p}], "temperature": 0.7}
            r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(body), timeout=30)
            if r.status_code != 200:
                return None
            content = r.json().get('choices',[{}])[0].get('message',{}).get('content','{}')
            return extract_json(content)
        def use_gemini(p):
            key = os.environ.get('GOOGLE_API_KEY')
            if not key:
                return None
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            body = {"contents": [{"parts": [{"text": p}]}]}
            r = requests.post(url, json=body, timeout=30)
            if r.status_code != 200:
                return None
            parts = r.json().get('candidates',[{}])[0].get('content',{}).get('parts',[{}])
            text = parts[0].get('text','{}')
            return extract_json(text)
        def use_deepseek(p):
            key = os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPEN_ROUTER_API_KEY')
            if not key:
                return None
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            body = {"model": os.environ.get('DEEPSEEK_MODEL','deepseek-chat'), "messages": [{"role":"user","content": p}], "temperature": 0.7}
            r = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, data=json.dumps(body), timeout=30)
            if r.status_code != 200:
                return None
            content = r.json().get('choices',[{}])[0].get('message',{}).get('content','{}')
            return extract_json(content)
        data_out = None
        if provider == 'openai':
            data_out = use_openai(prompt) or use_gemini(prompt)
        elif provider == 'gemini':
            data_out = use_gemini(prompt) or use_openai(prompt)
        else:
            data_out = use_deepseek(prompt) or use_openai(prompt)
        hs = [normalize_snippet(clamp(str(h), 40), 30) for h in (data_out.get('headlines') if isinstance(data_out, dict) else []) if str(h).strip()][:15]
        ds = [normalize_snippet(clamp(str(d), 110), 90) for d in (data_out.get('descriptions') if isinstance(data_out, dict) else []) if str(d).strip()][:4]
        
        # Validación estricta: Asegurar que ningún headline exceda 30 caracteres
        hs = [normalize_snippet(h, 30) for h in hs]
        ds = [normalize_snippet(d, 90) for d in ds]
        
        if not hs:
            # Fallbacks seguros de máximo 30 caracteres
            term_short = term[:20] if len(term) > 20 else term
            hs = [
                normalize_snippet(term_short, 30),
                normalize_snippet(f"{term_short} Hoy", 30),
                normalize_snippet(f"Expertos {term_short}", 30)
            ]
        if not ds:
            ds = [
                normalize_snippet(f"La mejor opción para {term}", 90),
                normalize_snippet(f"Descubre {term}", 90)
            ]
        
        result = jsonify({"success": True, "headlines": hs, "descriptions": ds})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/optimization/execute-skag', methods=['POST', 'OPTIONS'])
def execute_skag():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        campaign_id = data.get('campaignId')
        original_ad_group_id = data.get('originalAdGroupId')
        search_term = data.get('searchTerm', '')
        ad_variations = data.get('adVariations', [])  # NUEVO: Array de anuncios
        final_url = data.get('finalUrl', 'https://example.com/')  # URL común
        ad_group_name = data.get('adGroupName') or f"SKAG - {search_term}" # NUEVO: Nombre personalizado
        provider = (data.get('provider') or 'deepseek').lower()
        dry_run = bool(data.get('dryRun', False))
        
        print(f"📥 Recibiendo solicitud SKAG:")
        print(f"   - Nombre Grupo: {ad_group_name}")
        print(f"   - Número de anuncios: {len(ad_variations)}")
        print(f"   - Search term: {search_term}")
        
        if not all([customer_id, campaign_id, original_ad_group_id, search_term]):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"})
            res.status_code = 400
            res.headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_client_from_request()
        def extract_json(text):
            if not text:
                return None
            t = text.strip().replace('```json', '').replace('```', '')
            start = t.find('{')
            end = t.rfind('}')
            if start != -1 and end != -1 and end > start:
                t = t[start:end+1]
            t = t.replace('\u201c', '"').replace('\u201d', '"').replace('“', '"').replace('”', '"')
            try:
                return json.loads(t)
            except:
                return None

        def clamp(s, n):
            return (s or '')[:n]

        def generate_ad_copy(term, prov):
            prompt = (
                "Eres copywriter experto en Google Ads. Para el término dado genera JSON con 15 'headlines' (cada uno <=30 chars) y 4 'descriptions' (cada una <=90 chars). "
                "Incluye exactamente el término en el primer headline. Genera variaciones persuasivas en español. Responde SOLO JSON con {\"headlines\":[...15 items...],\"descriptions\":[...4 items...]}. "
                f"term: {term}"
            )
            last_error = None
            def use_openai(p):
                key = os.environ.get('OPENAI_API_KEY')
                if not key:
                    return None
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                body = {"model": os.environ.get('OPENAI_MODEL','gpt-4o-mini'), "messages": [{"role":"user","content": p}], "temperature": 0.7}
                r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(body), timeout=30)
                if r.status_code != 200:
                    last_error = r.text[:500]
                    return None
                content = r.json().get('choices',[{}])[0].get('message',{}).get('content','{}')
                return extract_json(content)
            def use_gemini(p):
                key = os.environ.get('GOOGLE_API_KEY')
                if not key:
                    return None
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
                body = {"contents": [{"parts": [{"text": p}]}]}
                r = requests.post(url, json=body, timeout=30)
                if r.status_code != 200:
                    last_error = r.text[:500]
                    return None
                parts = r.json().get('candidates',[{}])[0].get('content',{}).get('parts',[{}])
                text = parts[0].get('text','{}')
                return extract_json(text)
            def use_deepseek(p):
                key = os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPEN_ROUTER_API_KEY')
                if not key:
                    return None
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                body = {"model": os.environ.get('DEEPSEEK_MODEL','deepseek-chat'), "messages": [{"role":"user","content": p}], "temperature": 0.7}
                r = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, data=json.dumps(body), timeout=30)
                if r.status_code != 200:
                    last_error = r.text[:500]
                    return None
                content = r.json().get('choices',[{}])[0].get('message',{}).get('content','{}')
                return extract_json(content)
            data_out = None
            if prov == 'openai':
                data_out = use_openai(prompt) or use_gemini(prompt)
            elif prov == 'gemini':
                data_out = use_gemini(prompt) or use_openai(prompt)
            else:
                data_out = use_deepseek(prompt) or use_openai(prompt)
            if not isinstance(data_out, dict):
                return {
                    "headlines": [term, f"{term} Efectivo", f"{term} Profesional", f"Expertos en {term}", f"Consulta {term} Hoy", f"{term} Garantizado", f"Resultados {term}", f"{term} Confiable", f"Mejor {term}", f"{term} Rápido", f"{term} Seguro", f"{term} 24/7", f"Llama {term}", f"{term} Cerca", f"Top {term}"],
                    "descriptions": [f"La mejor opción para {term}. Resultados garantizados y rápidos. Consulta ahora.", f"Expertos en {term} con años de experiencia. Atención personalizada y confidencial.", f"Descubre {term} profesional. Primera consulta gratis. Contáctanos hoy mismo.", f"Servicio de {term} disponible 24/7. Soluciones efectivas para tus necesidades."]
                }
            hs = [clamp(str(h),30) for h in (data_out.get('headlines') or []) if str(h).strip()][:15]
            ds = [clamp(str(d),90) for d in (data_out.get('descriptions') or []) if str(d).strip()][:4]
            if len(hs) < 15:
                # Generate fallback headlines to complete to 15
                fallback_hs = [term, f"{term} Efectivo", f"{term} Profesional", f"Expertos {term}", f"Consulta {term}", f"{term} Garantizado", f"Resultados {term}", f"{term} Confiable", f"Mejor {term}", f"{term} Rápido", f"{term} Seguro", f"{term} 24/7", f"Llama {term}", f"{term} Cerca", f"Top {term}"]
                for fh in fallback_hs:
                    if len(hs) >= 15:
                        break
                    if fh not in hs:
                        hs.append(clamp(fh, 30))
            if len(ds) < 4:
                # Generate fallback descriptions to complete to 4
                fallback_ds = [
                    f"La mejor opción para {term}. Resultados garantizados y rápidos. Consulta ahora.",
                    f"Expertos en {term} con años de experiencia. Atención personalizada y confidencial.",
                    f"Descubre {term} profesional. Primera consulta gratis. Contáctanos hoy mismo.",
                    f"Servicio de {term} disponible 24/7. Soluciones efectivas para tus necesidades."
                ]
                for fd in fallback_ds:
                    if len(ds) >= 4:
                        break
                    if fd not in ds:
                        ds.append(clamp(fd, 90))
            return {"headlines": hs, "descriptions": ds}

        # Si no hay variaciones, generar una automáticamente
        if not ad_variations:
            gen = generate_ad_copy(search_term, provider)
            ad_variations.append({
                'headlines': gen.get('headlines', []),
                'descriptions': gen.get('descriptions', []),
                'finalUrl': final_url
            })

        def short_negative(s):
            stop = {"brujos","brujo","brujeria","de","la","las","el","los","en","y","para","que","un","una"}
            toks = [t for t in s.lower().split() if t not in stop]
            frag = ' '.join(toks).strip()
            return frag if frag else s
            
        if dry_run:
            created_group_name = f"SKAG - {search_term}"
            negative_exact = f"[{short_negative(search_term)}]"
            
            # Preparar preview de anuncios para dry run
            ads_preview = []
            for var in ad_variations:
                ads_preview.append({
                    "headlines": var.get('headlines', [search_term]),
                    "descriptions": var.get('descriptions', [f"La mejor opción para {search_term}"])
                })
                
            result = jsonify({
                "success": True,
                "dryRun": True,
                "message": "Simulación exitosa",
                "wouldCreate": {
                    "adGroupName": created_group_name,
                    "keywordExact": negative_exact,
                    "ads": ads_preview,
                    "negativeInOriginal": negative_exact,
                    "matchTypes": {
                        "exact": True,
                        "phrase": data.get('includePhraseMatch', True),
                        "broad": data.get('includeBroadMatch', False)
                    }
                }
            })
            result.headers.add('Access-Control-Allow-Origin', '*')
            return result
        client = ga
        ad_group_service = client.get_service("AdGroupService")
        ad_group_operation = client.get_type("AdGroupOperation")
        ad_group = ad_group_operation.create
        ad_group.name = f"SKAG - {search_term}"
        ad_group.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        ad_group_response = ad_group_service.mutate_ad_groups(customer_id=customer_id, operations=[ad_group_operation])
        new_ad_group_res = ad_group_response.results[0].resource_name
        new_ad_group_id = new_ad_group_res.split('/')[-1]
        
        # NUEVO: Obtener configuración de tipos de concordancia
        include_phrase = data.get('includePhraseMatch', True)  # Por defecto True
        include_broad = data.get('includeBroadMatch', False)   # Por defecto False
        base_cpc_micros = data.get('baseCpcMicros', 1000000)   # 1 COP por defecto
        
        # Crear keywords con estrategia multi-nivel
        ad_group_criterion_service = client.get_service("AdGroupCriterionService")
        keyword_operations = []
        
        # Helper para redondear CPC a unidad válida (1M micros = 1 unidad estándar)
        def round_cpc(micros):
            # Redondear al millón más cercano para evitar errores de "billable unit"
            # Ejemplo: 1,275,000,000 -> 1,275,000,000 (Ok)
            # Ejemplo: 1,275,500,000 -> 1,276,000,000 (Redondeo)
            unit = 1000000
            return int(round(micros / unit) * unit)

        # 1. EXACTA (siempre incluida) - CPC 100%
        kw_exact_op = client.get_type("AdGroupCriterionOperation")
        kw_exact = kw_exact_op.create
        kw_exact.ad_group = new_ad_group_res
        kw_exact.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        kw_exact.keyword = client.get_type("KeywordInfo")
        kw_exact.keyword.text = search_term
        kw_exact.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
        kw_exact.cpc_bid_micros = round_cpc(base_cpc_micros)
        keyword_operations.append(kw_exact_op)
        print(f"✅ Keyword EXACTA agregada: [{search_term}] - CPC: {kw_exact.cpc_bid_micros} micros")
        
        # 2. FRASE (opcional) - CPC 85%
        if include_phrase:
            kw_phrase_op = client.get_type("AdGroupCriterionOperation")
            kw_phrase = kw_phrase_op.create
            kw_phrase.ad_group = new_ad_group_res
            kw_phrase.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            kw_phrase.keyword = client.get_type("KeywordInfo")
            kw_phrase.keyword.text = search_term
            kw_phrase.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
            kw_phrase.cpc_bid_micros = round_cpc(base_cpc_micros * 0.85)
            keyword_operations.append(kw_phrase_op)
            print(f"✅ Keyword FRASE agregada: \"{search_term}\" - CPC: {kw_phrase.cpc_bid_micros} micros")
        
        # 3. AMPLIA (opcional) - CPC 70%
        if include_broad:
            kw_broad_op = client.get_type("AdGroupCriterionOperation")
            kw_broad = kw_broad_op.create
            kw_broad.ad_group = new_ad_group_res
            kw_broad.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            kw_broad.keyword = client.get_type("KeywordInfo")
            kw_broad.keyword.text = search_term
            kw_broad.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            kw_broad.cpc_bid_micros = round_cpc(base_cpc_micros * 0.70)
            keyword_operations.append(kw_broad_op)
            print(f"✅ Keyword AMPLIA agregada: {search_term} - CPC: {kw_broad.cpc_bid_micros} micros")
        
        # Ejecutar todas las operaciones de keywords en batch
        ad_group_criterion_service.mutate_ad_group_criteria(customer_id=customer_id, operations=keyword_operations)
        print(f"🎯 Total keywords creadas: {len(keyword_operations)}")
        
        # NUEVO: Crear múltiples anuncios RSA
        ad_group_ad_service = client.get_service("AdGroupAdService")
        ad_operations = []
        
        # Si no hay variaciones, usar fallback
        if not ad_variations:
            ad_variations = [{
                'headlines': [search_term, f"{search_term} oferta", f"{search_term} hoy"],
                'descriptions': [f"La mejor opción para {search_term}", f"Descubre {search_term}"],
                'finalUrl': final_url
            }]
        
        for idx, ad_copy in enumerate(ad_variations, 1):
            ad_group_ad_operation = client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.create
            ad_group_ad.ad_group = new_ad_group_res
            ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
            
            # URL final
            ad_final_url = ad_copy.get('finalUrl') or final_url
            ad_group_ad.ad.final_urls.append(ad_final_url)
            
            # Headlines
            headlines = ad_copy.get('headlines') or [search_term, f"{search_term} oferta", f"{search_term} hoy"]
            for i, h in enumerate(headlines):
                asset = client.get_type("AdTextAsset")
                asset.text = str(h)[:30]  # Truncar a 30 caracteres
                if i == 0:
                    asset.pinned_field = client.enums.ServedAssetFieldTypeEnum.HEADLINE_1
                ad_group_ad.ad.responsive_search_ad.headlines.append(asset)
            
            # Descriptions
            descriptions = ad_copy.get('descriptions') or [f"La mejor opción para {search_term}", f"Descubre {search_term}"]
            for d in descriptions:
                asset = client.get_type("AdTextAsset")
                asset.text = str(d)[:90]  # Truncar a 90 caracteres
                ad_group_ad.ad.responsive_search_ad.descriptions.append(asset)
            
            ad_operations.append(ad_group_ad_operation)
            print(f"✅ Anuncio #{idx} preparado: {len(headlines)} headlines, {len(descriptions)} descriptions")
        
        # Ejecutar todas las operaciones de anuncios en batch
        ad_group_ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=ad_operations)
        print(f"📢 Total anuncios RSA creados: {len(ad_operations)}")
        
        neg_op = client.get_type("AdGroupCriterionOperation")
        neg = neg_op.create
        neg.ad_group = f"customers/{customer_id}/adGroups/{original_ad_group_id}"
        neg.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        neg.negative = True
        neg.keyword = client.get_type("KeywordInfo")
        def short_negative(s):
            stop = {"brujos","brujo","brujeria","de","la","las","el","los","en","y","para","que","un","una"}
            toks = [t for t in s.lower().split() if t not in stop]
            frag = ' '.join(toks).strip()
            return frag if frag else s
        neg.keyword.text = short_negative(search_term)
        neg.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
        ad_group_criterion_service.mutate_ad_group_criteria(customer_id=customer_id, operations=[neg_op])
        result = jsonify({"success": True, "newAdGroupId": new_ad_group_id})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = []
        for error in ex.failure.errors:
            errors.append(error.message)
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/callouts/generate', methods=['POST', 'OPTIONS'])
def generate_callouts():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        keywords_raw = data.get('keywords', '')
        count = int(data.get('count', 4))
        provider = (data.get('provider') or 'deepseek').lower()
        seeds = [s.strip() for s in keywords_raw.split(',') if s.strip()]
        if not seeds:
            seeds = ['promoción']

        prompt = (
            "Eres copywriter experto en Google Ads. Genera N textos destacados (callouts) en JSON puro: "
            "[{\"text\"}] en español, cada \"text\" de máximo 25 caracteres, persuasivo y variado. "
            f"keywords: {', '.join(seeds)}; N: {count}. Responde SOLO JSON."
        )

        def extract_json(text):
            if not text:
                return None
            t = text.strip().replace('```json', '').replace('```', '')
            start = t.find('[')
            end = t.rfind(']')
            if start != -1 and end != -1 and end > start:
                t = t[start:end+1]
            t = t.replace('\u201c', '"').replace('\u201d', '"').replace('“', '"').replace('”', '"')
            try:
                return json.loads(t)
            except:
                return None

        last_error = None
        def use_openai(p):
            key = os.environ.get('OPENAI_API_KEY')
            if not key:
                return None
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            body = {"model": os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'), "messages": [{"role":"user","content": p}], "temperature": 0.8}
            r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(body), timeout=30)
            if r.status_code != 200:
                last_error = r.text[:500]
                return None
            content = r.json().get('choices',[{}])[0].get('message',{}).get('content','[]')
            return extract_json(content)
        def use_gemini(p):
            key = os.environ.get('GOOGLE_API_KEY')
            if not key:
                return None
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            body = {"contents": [{"parts": [{"text": p}]}]}
            r = requests.post(url, json=body, timeout=30)
            if r.status_code != 200:
                last_error = r.text[:500]
                return None
            parts = r.json().get('candidates',[{}])[0].get('content',{}).get('parts',[{}])
            text = parts[0].get('text','[]')
            return extract_json(text)
        def use_deepseek(p):
            key = os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPEN_ROUTER_API_KEY')
            if not key:
                return None
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            body = {"model": os.environ.get('DEEPSEEK_MODEL','deepseek-chat'), "messages": [{"role":"user","content": p}], "temperature": 0.8}
            r = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, data=json.dumps(body), timeout=30)
            if r.status_code != 200:
                last_error = r.text[:500]
                return None
            content = r.json().get('choices',[{}])[0].get('message',{}).get('content','[]')
            return extract_json(content)

        candidates = None
        if provider == 'deepseek':
            candidates = use_deepseek(prompt) or use_openai(prompt) or use_gemini(prompt)
        elif provider == 'openai':
            candidates = use_openai(prompt) or use_deepseek(prompt) or use_gemini(prompt)
        else:
            candidates = use_gemini(prompt) or use_deepseek(prompt) or use_openai(prompt)

        if not isinstance(candidates, list):
            return jsonify({"success": False, "message": "AI provider response unavailable", "details": last_error}), 500

        # Clamp to 25 chars, unique
        seen = set()
        out = []
        for item in candidates:
            t = str(item.get('text','')).strip()[:25]
            if not t or t in seen:
                continue
            seen.add(t)
            out.append({"text": t})
            if len(out) >= count:
                break
        return jsonify({"success": True, "callouts": out}), 200
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)})
        res.status_code = 500
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
@app.route('/api/ad/pause', methods=['POST', 'OPTIONS'])
def pause_ad():
    """
    Pausa un ad específico
    
    Request Body:
    {
        "customer_id": "1234567890",
        "ad_group_id": "9876543210",
        "ad_id": "12345678901234"
    }
    """
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        ad_group_id = data.get('ad_group_id')
        ad_id = data.get('ad_id')
        
        if not all([customer_id, ad_group_id, ad_id]):
            result = jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos',
                'required': ['customer_id', 'ad_group_id', 'ad_id']
            })
            result.status_code = 400
            result.headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        # Crear cliente
        client = get_client_from_request()
        ad_group_ad_service = client.get_service("AdGroupAdService")
        
        # Limpiar customer_id
        customer_id = customer_id.replace('-', '')
        
        # Crear resource name
        resource_name = ad_group_ad_service.ad_group_ad_path(
            customer_id,
            ad_group_id,
            ad_id
        )
        
        print(f"⏸️  Pausing ad: {resource_name}")
        
        # Crear operación de actualización
        ad_group_ad_operation = client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_group_ad_operation.update
        ad_group_ad.resource_name = resource_name
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED
        
        # Field mask - solo especificar el campo que cambia
        ad_group_ad_operation.update_mask.CopyFrom(
            FieldMask(paths=["status"])
        )
        
        # Ejecutar
        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=customer_id,
            operations=[ad_group_ad_operation]
        )
        
        print(f"✅ Ad paused successfully")
        
        result = jsonify({
            'success': True,
            'message': 'Anuncio pausado exitosamente',
            'resource_name': response.results[0].resource_name
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        error_message = f"Google Ads API Error: {ex.error.code().name}"
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': error_message,
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/keyword/update-bid', methods=['POST', 'OPTIONS'])
def update_keyword_bid():
    """
    Actualiza la puja CPC de una keyword
    
    Request Body:
    {
        "customer_id": "1234567890",
        "ad_group_id": "9876543210",
        "criterion_id": "12345678901234",
        "new_bid_micros": 5000000  // 5 USD en micros
    }
    """
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        ad_group_id = data.get('ad_group_id')
        criterion_id = data.get('criterion_id')
        new_bid_micros = data.get('new_bid_micros')
        
        if not all([customer_id, ad_group_id, criterion_id, new_bid_micros]):
            result = jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos',
                'required': ['customer_id', 'ad_group_id', 'criterion_id', 'new_bid_micros']
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        # Crear cliente
        client = get_client_from_request()
        ad_group_criterion_service = client.get_service("AdGroupCriterionService")
        
        # Limpiar customer_id
        customer_id = customer_id.replace('-', '')
        
        # Crear resource name
        resource_name = ad_group_criterion_service.ad_group_criterion_path(
            customer_id,
            ad_group_id,
            criterion_id
        )
        
        print(f"💰 Actualizando puja de keyword: {resource_name} → {new_bid_micros} micros")
        
        # Crear operación de actualización
        ad_group_criterion_operation = client.get_type("AdGroupCriterionOperation")
        ad_group_criterion = ad_group_criterion_operation.update
        ad_group_criterion.resource_name = resource_name
        ad_group_criterion.cpc_bid_micros = int(new_bid_micros)
        
        # Field mask - solo especificar el campo que cambia
        ad_group_criterion_operation.update_mask.CopyFrom(
            FieldMask(paths=["cpc_bid_micros"])
        )
        
        # Ejecutar
        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id,
            operations=[ad_group_criterion_operation]
        )
        
        print(f"✅ Puja actualizada exitosamente")
        
        result = jsonify({
            'success': True,
            'message': 'Puja de keyword actualizada exitosamente',
            'resource_name': response.results[0].resource_name
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        error_message = f"Google Ads API Error: {ex.error.code().name}"
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': error_message,
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result


# ==========================================
# ENDPOINT: Buscar Anuncios RSA
# ==========================================

@app.route('/api/search-ads', methods=['POST', 'OPTIONS'])
def search_ads():
    """
    Busca todos los anuncios RSA activos de una cuenta con métricas de los últimos 90 días
    
    Request Body:
    {
        "customerId": "1234567890",
        "limit": 200  // opcional, default 200
    }
    
    Response:
    {
        "success": true,
        "ads": [
            {
                "id": "12345678",
                "adGroupId": "98765432",
                "adGroupName": "Grupo de Anuncios 1",
                "campaignId": "11111111",
                "campaignName": "Campaña Test",
                "headlines": ["Titulo 1", "Titulo 2", ...],
                "descriptions": ["Descripcion 1", "Descripcion 2", ...],
                "finalUrl": "https://example.com",
                "status": "ENABLED",
                "metrics": {
                    "conversions": 42.5,
                    "clicks": 1234,
                    "conversionRate": 3.44
                }
            },
            ...
        ],
        "count": 42
    }
    """
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        customer_id = data.get('customerId')
        limit = data.get('limit', 200)
        
        # Validar
        if not customer_id:
            result = jsonify({
                'success': False,
                'error': 'Falta parámetro requerido: customerId'
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        # Crear cliente
        client = get_client_from_request()
        ga_service = client.get_service("GoogleAdsService")
        
        # Limpiar customer_id
        customer_id = customer_id.replace('-', '')
        
        print(f"🔍 Buscando anuncios RSA con métricas para customer {customer_id}")
        
        # Calcular últimos 90 días
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        date_range = f"segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'"
        
        # Query GAQL para obtener anuncios RSA con métricas
        query = f"""
            SELECT 
                ad_group_ad.ad.id,
                ad_group_ad.ad.name,
                ad_group_ad.ad.responsive_search_ad.headlines,
                ad_group_ad.ad.responsive_search_ad.descriptions,
                ad_group_ad.ad.final_urls,
                ad_group_ad.status,
                ad_group.id,
                ad_group.name,
                campaign.id,
                campaign.name,
                metrics.conversions,
                metrics.clicks,
                metrics.conversions_from_interactions_rate
            FROM ad_group_ad
            WHERE ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
                AND ad_group_ad.status != 'REMOVED'
                AND {date_range}
            ORDER BY ad_group_ad.ad.id DESC
            LIMIT {limit}
        """
        
        response = ga_service.search(
            customer_id=customer_id,
            query=query
        )
        
        ads = []
        for row in response:
            ad = row.ad_group_ad.ad
            ad_group = row.ad_group
            campaign = row.campaign
            status = row.ad_group_ad.status
            metrics = row.metrics
            
            # Extraer headlines
            headlines = []
            if ad.responsive_search_ad and ad.responsive_search_ad.headlines:
                headlines = [h.text for h in ad.responsive_search_ad.headlines]
            
            # Extraer descriptions
            descriptions = []
            if ad.responsive_search_ad and ad.responsive_search_ad.descriptions:
                descriptions = [d.text for d in ad.responsive_search_ad.descriptions]
            
            # Extraer final URL
            final_url = ad.final_urls[0] if ad.final_urls else ""
            
            # Extraer métricas
            conversions = float(metrics.conversions) if hasattr(metrics, 'conversions') else 0
            clicks = int(metrics.clicks) if hasattr(metrics, 'clicks') else 0
            conversion_rate = float(metrics.conversions_from_interactions_rate) * 100 if hasattr(metrics, 'conversions_from_interactions_rate') else 0
            
            ads.append({
                'id': str(ad.id),
                'adGroupId': str(ad_group.id),
                'adGroupName': ad_group.name,
                'campaignId': str(campaign.id),
                'campaignName': campaign.name,
                'headlines': headlines,
                'descriptions': descriptions,
                'finalUrl': final_url,
                'status': status.name,
                'metrics': {
                    'conversions': round(conversions, 1),
                    'clicks': clicks,
                    'conversionRate': round(conversion_rate, 2)
                }
            })
        
        print(f"✅ Encontrados {len(ads)} anuncios RSA con métricas")
        
        result = jsonify({
            'success': True,
            'ads': ads,
            'count': len(ads)
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        error_message = f"Google Ads API Error: {ex.error.code().name}"
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': error_message,
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result


# ==========================================
# ENDPOINT: Listar Campañas
# ==========================================

@app.route('/api/campaigns', methods=['POST', 'OPTIONS'])
def list_campaigns():
    """
    Lista todas las campañas de una cuenta
    """
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        customer_id = data.get('customerId')
        
        if not customer_id:
            result = jsonify({
                'success': False,
                'error': 'Falta parámetro requerido: customerId'
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        client = get_client_from_request()
        ga_service = client.get_service("GoogleAdsService")
        customer_id = customer_id.replace('-', '')
        
        print(f"📋 Listando campañas para customer {customer_id}")
        
        query = """
            SELECT 
                campaign.id,
                campaign.name,
                campaign.status
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.name
        """
        
        response = ga_service.search(
            customer_id=customer_id,
            query=query
        )
        
        campaigns = []
        for row in response:
            campaigns.append({
                'id': str(row.campaign.id),
                'name': row.campaign.name,
                'status': row.campaign.status.name
            })
        
        print(f"✅ Encontradas {len(campaigns)} campañas")
        
        result = jsonify({
            'success': True,
            'campaigns': campaigns,
            'count': len(campaigns)
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': 'Google Ads API Error',
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result


# ==========================================
# ENDPOINT: Listar Grupos de Anuncios
# ==========================================

@app.route('/api/adgroups', methods=['POST', 'OPTIONS'])
def list_adgroups():
    """
    Lista todos los grupos de anuncios de una campaña
    """
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        customer_id = data.get('customerId')
        campaign_id = data.get('campaignId')
        
        if not customer_id or not campaign_id:
            result = jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos: customerId, campaignId'
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        client = get_client_from_request()
        ga_service = client.get_service("GoogleAdsService")
        customer_id = customer_id.replace('-', '')
        
        print(f"📋 Listando grupos de anuncios para campaña {campaign_id}")
        
        query = f"""
            SELECT 
                ad_group.id,
                ad_group.name,
                ad_group.status
            FROM ad_group
            WHERE campaign.id = {campaign_id}
                AND ad_group.status != 'REMOVED'
            ORDER BY ad_group.name
        """
        
        response = ga_service.search(
            customer_id=customer_id,
            query=query
        )
        
        ad_groups = []
        for row in response:
            ad_groups.append({
                'id': str(row.ad_group.id),
                'name': row.ad_group.name,
                'status': row.ad_group.status.name
            })
        
        print(f"✅ Encontrados {len(ad_groups)} grupos de anuncios")
        
        result = jsonify({
            'success': True,
            'adGroups': ad_groups,
            'count': len(ad_groups)
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': 'Google Ads API Error',
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

# ============================================================================
# CAMPAIGN CREATION ENDPOINTS
# ============================================================================

@app.route('/api/create-budget', methods=['POST', 'OPTIONS'])
def create_campaign_budget():
    """Crea un presupuesto de campaña"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId', '').replace('-', '')
        name = data.get('name')
        amount_micros = int(data.get('amountMicros', 0))
        
        if not all([customer_id, name, amount_micros]):
            result = jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos'
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        print(f"💰 Creando budget: {name} con ${amount_micros/1_000_000} COP")
        
        client = get_client_from_request()
        campaign_budget_service = client.get_service("CampaignBudgetService")
        
        campaign_budget_operation = client.get_type("CampaignBudgetOperation")
        campaign_budget = campaign_budget_operation.create
        
        campaign_budget.name = name
        campaign_budget.amount_micros = amount_micros
        campaign_budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        
        response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id,
            operations=[campaign_budget_operation]
        )
        
        resource_name = response.results[0].resource_name
        print(f"✅ Budget creado: {resource_name}")
        
        result = jsonify({
            'success': True,
            'resourceName': resource_name
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': 'Google Ads API Error',
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/create-campaign', methods=['POST', 'OPTIONS'])
def create_campaign():
    """Crea una campaña de búsqueda"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId', '').replace('-', '')
        name = data.get('name')
        budget_resource_name = data.get('budgetResourceName')
        status = data.get('status', 'PAUSED')
        
        if not all([customer_id, name, budget_resource_name]):
            result = jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos'
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        print(f"🚀 Creando campaña: {name}")
        
        client = get_client_from_request()
        campaign_service = client.get_service("CampaignService")
        
        campaign_operation = client.get_type("CampaignOperation")
        campaign = campaign_operation.create
        
        campaign.name = name
        campaign.campaign_budget = budget_resource_name
        
        if status == "ENABLED":
            campaign.status = client.enums.CampaignStatusEnum.ENABLED
        elif status == "PAUSED":
            campaign.status = client.enums.CampaignStatusEnum.PAUSED
        else:
            campaign.status = client.enums.CampaignStatusEnum.PAUSED
        
        campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
        
        # Campo start_date puede ser requerido en algunas versiones
        campaign.start_date = (date.today()).strftime('%Y%m%d')
        # Campo requerido para cumplir con regulaciones EU
        # Campo EU Political Advertising usando el enum correcto
        try:
            from google.ads.googleads.v22.enums.types.campaign_contains_eu_political_advertising import CampaignContainsEuPoliticalAdvertisingEnum
            campaign.contains_eu_political_advertising = CampaignContainsEuPoliticalAdvertisingEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
        except ImportError:
            # Fallback: usar el valor numérico directamente (2 = DOES_NOT_CONTAIN)
            campaign.contains_eu_political_advertising = 2
        campaign.manual_cpc.enhanced_cpc_enabled = False
        
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        campaign.network_settings.target_content_network = False
        campaign.network_settings.target_partner_search_network = False
        
        
        print(f"DEBUG - Campaign antes de mutation:")
        print(f"  name: {campaign.name}")
        print(f"  budget: {campaign.campaign_budget}")
        print(f"  contains_eu_political_advertising: {campaign.contains_eu_political_advertising}")
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id,
            operations=[campaign_operation]
        )
        
        resource_name = response.results[0].resource_name
        campaign_id = resource_name.split('/')[-1]
        
        print(f"✅ Campaña creada: {resource_name}")
        
        result = jsonify({
            'success': True,
            'resourceName': resource_name,
            'campaignId': campaign_id
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': 'Google Ads API Error',
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/create-adgroup', methods=['POST', 'OPTIONS'])
def create_ad_group_copy():
    """Crea un grupo de anuncios"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId', '').replace('-', '')
        campaign_id = data.get('campaignId')
        name = data.get('name')
        cpc_bid_micros = int(data.get('cpcBidMicros', 0))
        
        if not all([customer_id, campaign_id, name]):
            result = jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos'
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        print(f"📂 Creando ad group: {name}")
        
        client = get_client_from_request()
        ad_group_service = client.get_service("AdGroupService")
        
        ad_group_operation = client.get_type("AdGroupOperation")
        ad_group = ad_group_operation.create
        
        ad_group.name = name
        ad_group.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        
        # Validar CPC mínimo para COP (Pesos Colombianos)
        # Mínimo: 40 COP = 40,000,000 micros
        min_cpc = 40_000_000
        if cpc_bid_micros > 0:
            # Asegurar mínimo
            if cpc_bid_micros < min_cpc:
                cpc_bid_micros = min_cpc
            # Redondear a múltiplo de 10,000
            cpc_bid_micros = (cpc_bid_micros // 10_000) * 10_000
            if cpc_bid_micros < min_cpc:
                cpc_bid_micros = min_cpc
            ad_group.cpc_bid_micros = cpc_bid_micros
        else:
            # Si no se proporciona, usar mínimo por defecto
            ad_group.cpc_bid_micros = min_cpc
        
        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id,
            operations=[ad_group_operation]
        )
        
        resource_name = response.results[0].resource_name
        ad_group_id = resource_name.split('/')[-1]
        
        print(f"✅ Ad Group creado: {resource_name}")
        
        result = jsonify({
            'success': True,
            'resourceName': resource_name,
            'adGroupId': ad_group_id
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': 'Google Ads API Error',
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/create-keyword', methods=['POST', 'OPTIONS'])
def create_keyword():
    """Crea una keyword en un ad group"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId', '').replace('-', '')
        ad_group_id = data.get('adGroupId')
        keyword_text = data.get('keywordText')
        match_type = data.get('matchType', 'BROAD')
        cpc_bid_micros = data.get('cpcBidMicros')
        
        if not all([customer_id, ad_group_id, keyword_text]):
            result = jsonify({
                'success': False,
                'error': 'Faltan parámetros requeridos'
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        print(f"🔑 Creando keyword: {keyword_text} ({match_type})")
        
        client = get_client_from_request()
        ad_group_criterion_service = client.get_service("AdGroupCriterionService")
        
        operation = client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        
        criterion.ad_group = f"customers/{customer_id}/adGroups/{ad_group_id}"
        criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        criterion.keyword.text = keyword_text
        
        if match_type == "EXACT":
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
        elif match_type == "PHRASE":
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
        else:
            criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
        
        if cpc_bid_micros and int(cpc_bid_micros) > 0:
            criterion.cpc_bid_micros = int(cpc_bid_micros)
        
        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=customer_id,
            operations=[operation]
        )
        
        resource_name = response.results[0].resource_name
        print(f"✅ Keyword creada: {resource_name}")
        
        result = jsonify({
            'success': True,
            'resourceName': resource_name
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': 'Google Ads API Error',
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

# Agregar este endpoint al final de app.py antes de la última línea

@app.route('/api/query', methods=['POST', 'OPTIONS'])
def execute_query():
    """Ejecuta una query GAQL personalizada"""
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        customer_id = data.get('customerId', '').replace('-', '')
        query = data.get('query')
        
        if not customer_id or not query:
            result = jsonify({
                'success': False,
                'error': 'customerId y query son requeridos'
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        print(f"📊 Ejecutando query para cuenta {customer_id}")
        print(f"📝 Query: {query[:200]}...")
        
        client = get_client_from_request()
        ga_service = client.get_service("GoogleAdsService")
        
        # Ejecutar búsqueda
        search_request = client.get_type("SearchGoogleAdsStreamRequest")
        search_request.customer_id = customer_id
        search_request.query = query
        
        results_list = []
        stream = ga_service.search_stream(search_request)
        
        for batch in stream:
            for row in batch.results:
                # Convertir el resultado a diccionario
                row_dict = {}
                
                # customer_client (para queries de cuentas MCC)
                if hasattr(row, 'customer_client'):
                    client = row.customer_client
                    row_dict['customerClient'] = {
                        'id': str(client.id),
                        'descriptiveName': client.descriptive_name,
                        'currencyCode': client.currency_code,
                        'timeZone': client.time_zone,
                        'status': client.status.name if hasattr(client, 'status') else 'UNKNOWN'
                    }
                
                # customer (para queries de información de cuenta)
                if hasattr(row, 'customer'):
                    customer = row.customer
                    row_dict['customer'] = {
                        'id': str(customer.id),
                        'descriptiveName': customer.descriptive_name,
                        'currencyCode': customer.currency_code,
                        'timeZone': customer.time_zone,
                        'status': customer.status.name if hasattr(customer, 'status') else 'UNKNOWN'
                    }
                
                # Extraer campos según lo que tenga el row
                if hasattr(row, 'ad_group_criterion'):
                    criterion = row.ad_group_criterion
                    row_dict['adGroupCriterion'] = {
                        'criterionId': str(criterion.criterion_id),
                        'status': criterion.status.name if hasattr(criterion, 'status') else None,
                    }
                    
                    if hasattr(criterion, 'keyword'):
                        row_dict['adGroupCriterion']['keyword'] = {
                            'text': criterion.keyword.text,
                            'matchType': criterion.keyword.match_type.name
                        }
                    
                    if hasattr(criterion, 'quality_info'):
                        qi = criterion.quality_info
                        row_dict['adGroupCriterion']['qualityInfo'] = {
                            'qualityScore': qi.quality_score if hasattr(qi, 'quality_score') else None
                        }
                
                if hasattr(row, 'ad_group'):
                    row_dict['adGroup'] = {
                        'id': str(row.ad_group.id),
                        'name': row.ad_group.name
                    }
                
                if hasattr(row, 'ad_group_ad'):
                    ad_group_ad = row.ad_group_ad
                    row_dict['adGroupAd'] = {
                        'status': ad_group_ad.status.name if hasattr(ad_group_ad, 'status') else None
                    }
                    
                    if hasattr(ad_group_ad, 'ad'):
                        ad = ad_group_ad.ad
                        ad_dict = {
                            'id': str(ad.id),
                            'type': ad.type_.name if hasattr(ad, 'type_') else None
                        }
                        
                        if hasattr(ad, 'responsive_search_ad'):
                            rsa = ad.responsive_search_ad
                            ad_dict['responsiveSearchAd'] = {
                                'headlines': [{'text': h.text} for h in rsa.headlines] if hasattr(rsa, 'headlines') else [],
                                'descriptions': [{'text': d.text} for d in rsa.descriptions] if hasattr(rsa, 'descriptions') else []
                            }
                        
                        row_dict['adGroupAd']['ad'] = ad_dict
                
                if hasattr(row, 'campaign'):
                    row_dict['campaign'] = {
                        'id': str(row.campaign.id),
                        'name': row.campaign.name
                    }
                
                if hasattr(row, 'metrics'):
                    metrics = row.metrics
                    row_dict['metrics'] = {
                        'impressions': str(metrics.impressions) if hasattr(metrics, 'impressions') else '0',
                        'clicks': str(metrics.clicks) if hasattr(metrics, 'clicks') else '0',
                        'costMicros': str(metrics.cost_micros) if hasattr(metrics, 'cost_micros') else '0',
                        'conversions': metrics.conversions if hasattr(metrics, 'conversions') else 0.0,
                        'ctr': metrics.ctr if hasattr(metrics, 'ctr') else 0.0,
                        'conversionsFromInteractionsRate': metrics.conversions_from_interactions_rate if hasattr(metrics, 'conversions_from_interactions_rate') else 0.0
                    }
                
                results_list.append(row_dict)
        
        print(f"✅ Query ejecutada exitosamente. Resultados: {len(results_list)}")
        
        result = jsonify({
            'success': True,
            'results': results_list,
            'count': len(results_list)
        }), 200
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error: {ex}")
        errors = []
        if ex.failure:
            for error in ex.failure.errors:
                errors.append(error.message)
        
        result = jsonify({
            'success': False,
            'error': 'Google Ads API Error',
            'errors': errors
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        result = jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

# Run server (after all routes are registered)
@app.route('/api/keyword-ideas', methods=['POST', 'OPTIONS'])
def get_keyword_ideas():
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,login-customer-id')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    try:
        data = request.json
        customer_id = data.get('customerId')
        keyword_texts = data.get('keywords', [])
        page_url = data.get('pageUrl')
        
        # Validar que al menos uno exista
        if not keyword_texts and not page_url:
            return jsonify({'error': 'Must provide either keywords or pageUrl'}), 400

        # Obtener cliente
        client = get_client_from_request()

        service = client.get_service("KeywordPlanIdeaService")
        request_data = client.get_type("GenerateKeywordIdeasRequest")
        request_data.customer_id = customer_id
        # Idioma español (1003) por defecto, ubicación Colombia (2170) por defecto
        # TODO: Hacer esto configurable desde el frontend
        request_data.language = "languageConstants/1003"
        request_data.geo_target_constants = ["geoTargetConstants/2170"]
        request_data.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS

        # Configurar seed
        if keyword_texts:
            request_data.keyword_seed.keywords.extend(keyword_texts)
        elif page_url:
            request_data.url_seed.url = page_url

        response = service.generate_keyword_ideas(request=request_data)

        results = []
        for idea in response:
            metrics = idea.keyword_idea_metrics
            
            monthly_volumes = []
            if hasattr(metrics, 'monthly_search_volumes'):
                for volume in metrics.monthly_search_volumes:
                    monthly_volumes.append({
                        "month": volume.month.name,
                        "year": str(volume.year),
                        "count": str(volume.monthly_searches)
                    })

            result = {
                "text": idea.text,
                "avg_monthly_searches": str(metrics.avg_monthly_searches),
                "competition": metrics.competition.name,
                "competition_index": str(metrics.competition_index),
                "low_top_of_page_bid_micros": str(metrics.low_top_of_page_bid_micros),
                "high_top_of_page_bid_micros": str(metrics.high_top_of_page_bid_micros),
                "monthly_search_volumes": monthly_volumes
            }
            results.append(result)
            
        result = jsonify({'results': results})
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result

    except Exception as e:
        print(f"Error generating keyword ideas: {e}")
        # Print stack trace for debugging
        import traceback
        traceback.print_exc()
        result = jsonify({'error': str(e)}), 500
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result

@app.route('/api/trends', methods=['POST', 'OPTIONS'])
def get_google_trends():
    """
    Obtiene datos de tendencias usando estrategia híbrida de 3 niveles:
    1. Google Ads Keyword Planner API (primario - siempre disponible)
    2. Pytrends (secundario - si está disponible)
    3. Datos sintéticos basados en Google Ads (fallback)
    
    Parámetros:
    - keywords: Lista de términos de búsqueda
    - geo: Código de país (ej. "US", "MX", "ES", "" para global)
    - timeRange: Rango de tiempo
    - category: ID de categoría (0 = todas)
    - property: Plataforma ("" = Web, "youtube", "images", "news", "froogle")
    - resolution: Granularidad geográfica ("COUNTRY", "REGION", "DMA", "CITY")
    """
    
    # CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Google-Ads-Refresh-Token,X-Google-Ads-Login-Customer-Id')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        keywords = data.get('keywords', [])
        geo = data.get('geo', '')
        time_range = data.get('timeRange', 'today 12-m')
        category = data.get('category', 0)
        gprop = data.get('property', '')
        resolution = data.get('resolution', 'COUNTRY')
        
        if not keywords or len(keywords) == 0:
            return jsonify({'success': False, 'error': 'Se requiere al menos un keyword'}), 400
        
        print(f"🔍 Trends Request: {keywords} | Geo: {geo or 'Global'} | Range: {time_range}")
        
        # NIVEL 1: Intentar con Scraping Manual (PRIORIDAD MÁXIMA)
        try:
            print("🔄 Intentando Nivel 1: Scraping Manual...")
            # Habilitamos bajo volumen para tener TODAS las ubicaciones en el CSV
            result_data = get_trends_via_scraping(keywords, geo, time_range, resolution)
            print("✅ Datos obtenidos de Scraping Manual")
            
            result = jsonify(result_data)
            result.headers.add('Access-Control-Allow-Origin', '*')
            return result
        except Exception as scraping_error:
            print(f"⚠️ Scraping Manual falló: {str(scraping_error)}")

        # NIVEL 2: Intentar con Google Ads API (SECUNDARIO - Robusto, sin regiones)
        try:
            print("🔄 Intentando Nivel 2: Google Ads API...")
            result_data = get_trends_from_google_ads(keywords, geo, time_range, resolution)
            print("✅ Datos obtenidos de Google Ads API")
            
            result = jsonify(result_data)
            result.headers.add('Access-Control-Allow-Origin', '*')
            return result
            
        except Exception as ads_error:
            print(f"⚠️ Google Ads API falló: {str(ads_error)}")
        
        # NIVEL 3: Fallback a datos sintéticos (SIEMPRE FUNCIONA)
        print("ℹ️ Usando datos sintéticos como fallback")
        result_data = generate_synthetic_trends_data(keywords, geo, time_range, resolution)
        
        result = jsonify(result_data)
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
    
    except Exception as e:
        print(f"❌ Error crítico en Trends API: {str(e)}")
        import traceback
        traceback.print_exc()
        
        result = jsonify({'success': False, 'error': str(e)}), 500
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result


def get_trends_from_google_ads(keywords, geo, time_range, resolution):
    """Obtiene datos de tendencias usando Google Ads Keyword Planner API"""
    
    # Crear cliente de Google Ads
    client = get_client_from_request()
    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
    
    # Mapear geo code a Google Ads geo target constant
    geo_target_constants = []
    if geo:
        geo_map = {
            'US': '2840', 'MX': '2484', 'ES': '2724', 'CO': '2170',
            'AR': '2032', 'CL': '2152', 'PE': '2604', 'VE': '2862'
        }
        if geo in geo_map:
            geo_target_constants.append(
                client.get_service("GeoTargetConstantService").geo_target_constant_path(geo_map[geo])
            )
    
    # Construir request
    request_data = client.get_type("GenerateKeywordIdeasRequest")
    request_data.customer_id = request.headers.get('X-Google-Ads-Login-Customer-Id') or os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    request_data.language = client.get_service("GoogleAdsService").language_constant_path("1000")  # Español
    
    if geo_target_constants:
        request_data.geo_target_constants.extend(geo_target_constants)
    
    request_data.keyword_seed.keywords.extend(keywords)
    
    # Ejecutar request
    response = keyword_plan_idea_service.generate_keyword_ideas(request=request_data)
    
    # Procesar resultados
    timeline_data = []
    region_data = []
    related_queries = []
    
    from datetime import datetime, timedelta
    import random
    
    for idea in response:
        metrics = idea.keyword_idea_metrics
        
        # Generar timeline basado en monthly_search_volumes
        if hasattr(metrics, 'monthly_search_volumes') and metrics.monthly_search_volumes:
            for volume in metrics.monthly_search_volumes:
                timeline_data.append({
                    'date': f"{volume.year}-{volume.month.value:02d}-01",
                    'value': int(volume.monthly_searches)
                })
        
        # Agregar términos relacionados
        if idea.text not in keywords and idea.text not in related_queries:
            related_queries.append(idea.text)
    
    # Generar datos de región (SOLO NIVEL PAÍS para ser honestos con los datos)
    # Google Ads API no entrega desglose regional, así que devolvemos el total del país
    # en lugar de inventar una distribución simulada.
    if geo:
        # Mapeo de códigos a nombres para visualización
        country_names = {
            'US': 'Estados Unidos', 'MX': 'México', 'ES': 'España', 'CO': 'Colombia',
            'AR': 'Argentina', 'CL': 'Chile', 'PE': 'Perú', 'VE': 'Venezuela'
        }
        country_name = country_names.get(geo, geo)
        
        region_data = [{
            'geoName': country_name,
            'value': 100, # 100% del interés está en el país (dato real)
            'geoCode': geo
        }]
    
    # Ordenar timeline por fecha
    timeline_data.sort(key=lambda x: x['date'])
    
    return {
        'timelineData': timeline_data[-12:] if timeline_data else None,  # Últimos 12 meses
        'interestByRegion': region_data if region_data else None,
        'relatedQueries': related_queries[:10] if related_queries else None,
        'source': 'google_ads'
    }


def get_trends_from_pytrends(keywords, geo, time_range, gprop, resolution):
    """Obtiene datos de Pytrends (solo si está disponible)"""
    
    from pytrends.request import TrendReq
    
    # Configurar headers para simular un navegador real y evitar bloqueo
    requests_args = {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
        }
    }
    
    # Inicializar con reintentos y backoff
    pytrends = TrendReq(
        hl='es-ES', 
        tz=360, 
        retries=3, 
        backoff_factor=0.5,
        requests_args=requests_args
    )
    
    pytrends.build_payload(kw_list=keywords[:5], timeframe=time_range, geo=geo, gprop=gprop)
    
    timeline_data = []
    region_data = []
    related_queries = []
    
    # Timeline
    try:
        interest_over_time_df = pytrends.interest_over_time()
        if not interest_over_time_df.empty:
            for index, row in interest_over_time_df.iterrows():
                value = int(row[keywords[0]]) if keywords[0] in row else 0
                timeline_data.append({'date': index.strftime('%Y-%m-%d'), 'value': value})
    except Exception as e:
        print(f"⚠️ Error en timeline: {str(e)}")
    
    # Regiones - FIXED: Properly handle metro/region data
    try:
        # Determine resolution parameter for pytrends
        # Pytrends supports: COUNTRY, REGION, DMA, CITY
        pytrends_resolution = resolution
        
        # Safety check
        if pytrends_resolution not in ['COUNTRY', 'REGION', 'DMA', 'CITY']:
            pytrends_resolution = 'COUNTRY'
            
        print(f"📍 Pytrends Resolution: {pytrends_resolution} (Requested: {resolution})")
        
        interest_by_region_df = pytrends.interest_by_region(
            resolution=pytrends_resolution,
            inc_low_vol=True, # TRUE para tener todas las ubicaciones en el CSV
            inc_geo_code=False  # Geo codes not always available
        )
        
        if not interest_by_region_df.empty and keywords[0] in interest_by_region_df.columns:
            # Sort by interest value
            interest_by_region_df = interest_by_region_df.sort_values(by=keywords[0], ascending=False)
            
            # Get all regions with non-zero values (no limit)
            for region_name, row in interest_by_region_df.iterrows():
                value = int(row[keywords[0]]) if keywords[0] in row else 0
                if value > 0:
                    region_data.append({
                        'geoName': str(region_name),  # This will be "Phoenix AZ", "Los Angeles CA", etc.
                        'value': value,
                        'geoCode': None
                    })
            
            print(f"✅ Pytrends regions: {len(region_data)} encontradas")
    except Exception as e:
        print(f"⚠️ Error en regiones: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Related queries
    try:
        related_dict = pytrends.related_queries()
        if keywords[0] in related_dict:
            if 'rising' in related_dict[keywords[0]] and related_dict[keywords[0]]['rising'] is not None:
                related_queries = related_dict[keywords[0]]['rising']['query'].head(10).tolist()
            elif 'top' in related_dict[keywords[0]] and related_dict[keywords[0]]['top'] is not None:
                related_queries = related_dict[keywords[0]]['top']['query'].head(10).tolist()
    except Exception as e:
        print(f"⚠️ Error en related queries: {str(e)}")
    
    return {
        'timelineData': timeline_data if timeline_data else None,
        'interestByRegion': region_data if region_data else None,
        'relatedQueries': related_queries if related_queries else None,
        'source': 'pytrends'
    }


def generate_synthetic_trends_data(keywords, geo, time_range, resolution):
    """Genera datos sintéticos realistas como fallback"""
    
    from datetime import datetime, timedelta
    import random
    
    # Generar timeline sintético
    months = 12 if '12-m' in time_range else 3 if '3-m' in time_range else 1
    timeline_data = []
    base_value = random.randint(50, 100)
    
    for i in range(months):
        date = datetime.now() - timedelta(days=30 * (months - i))
        # Simular tendencia con variación
        trend = base_value + random.randint(-20, 20) + (i * 2)  # Tendencia ligeramente creciente
        timeline_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'value': max(0, min(100, trend))
        })
    
    # Generar datos de región
    region_data = generate_region_data_for_country(geo, resolution, base_value * 1000)
    
    # Generar términos relacionados sintéticos
    related_queries = [
        f"{keywords[0]} online",
        f"{keywords[0]} gratis",
        f"mejor {keywords[0]}",
        f"{keywords[0]} 2024",
        f"comprar {keywords[0]}"
    ]
    
    return {
        'timelineData': timeline_data,
        'interestByRegion': region_data[:10],
        'relatedQueries': related_queries,
        'source': 'synthetic'
    }


def generate_region_data_for_country(geo, resolution, total_volume, keyword_seed=None):
    """Genera datos de región basados en el país y granularidad, con variación por keyword"""
    
    import random
    
    # Usar el keyword como semilla para que la aleatoriedad sea consistente por término
    if keyword_seed:
        random.seed(sum(ord(c) for c in keyword_seed))
    
    regions_by_country = {
        'US': {
            'REGION': ['California', 'Texas', 'Florida', 'New York', 'Illinois', 'Pennsylvania', 'Ohio', 'Georgia', 'North Carolina', 'Michigan'],
            'DMA': ['New York NY', 'Los Angeles CA', 'Chicago IL', 'Philadelphia PA', 'Dallas-Ft. Worth TX', 'San Francisco-Oakland-San Jose CA', 'Atlanta GA', 'Houston TX', 'Washington DC', 'Boston MA-Manchester NH'],
            'CITY': ['Los Angeles', 'New York', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']
        },
        'MX': {
            'REGION': ['Ciudad de México', 'Jalisco', 'Nuevo León', 'Estado de México', 'Puebla', 'Veracruz', 'Guanajuato', 'Baja California', 'Chihuahua', 'Sonora'],
            'DMA': ['Área Metropolitana CDMX', 'Monterrey', 'Guadalajara', 'Puebla', 'Tijuana', 'León', 'Mérida', 'San Luis Potosí', 'Querétaro', 'Toluca'],
            'CITY': ['Ciudad de México', 'Guadalajara', 'Monterrey', 'Puebla', 'Tijuana', 'León', 'Juárez', 'Zapopan', 'Mérida', 'San Luis Potosí']
        },
        'ES': {
            'REGION': ['Madrid', 'Cataluña', 'Andalucía', 'Valencia', 'País Vasco', 'Galicia', 'Castilla y León', 'Canarias', 'Aragón', 'Murcia'],
            'DMA': ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao', 'Málaga', 'Zaragoza', 'Alicante', 'Las Palmas', 'Murcia'],
            'CITY': ['Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao', 'Málaga', 'Zaragoza', 'Murcia', 'Palma', 'Las Palmas']
        }
    }
    
    # Fallback para otros países (lista genérica de "Región X")
    if geo not in regions_by_country:
        return [{'geoName': f"{geo} Region 1", 'value': 100, 'geoCode': None}]
        
    if resolution not in regions_by_country[geo]:
        # Si la resolución no está definida, usar la primera disponible o fallback
        available_resolutions = list(regions_by_country[geo].keys())
        if available_resolutions:
            resolution = available_resolutions[0]
        else:
            return [{'geoName': geo or 'Global', 'value': 100, 'geoCode': None}]
    
    regions = regions_by_country[geo][resolution].copy()
    
    # Mezclar regiones aleatoriamente (pero consistente con la semilla)
    random.shuffle(regions)
    
    # Tomar top 5-8 regiones
    num_regions = random.randint(5, min(len(regions), 8))
    selected_regions = regions[:num_regions]
    
    region_data = []
    
    # Generar porcentajes distribuidos aleatoriamente
    remaining_value = 100
    for i, region in enumerate(selected_regions):
        if i == len(selected_regions) - 1:
            value = max(1, remaining_value) # El último toma el resto
        else:
            # Valor aleatorio decreciente
            max_val = int(remaining_value * 0.6)
            min_val = int(remaining_value * 0.1)
            value = random.randint(min_val, max(min_val + 1, max_val))
            remaining_value -= value
            
        region_data.append({
            'geoName': region,
            'value': value,
            'geoCode': f"{geo}-{i+1}"
        })
    
    # Ordenar por valor descendente
    region_data.sort(key=lambda x: x['value'], reverse=True)
    
    return region_data

def get_trends_via_scraping(keywords, geo, time_range, resolution):
    """
    Intenta obtener datos 'rascando' directamente la web de Google Trends
    simulando una sesión de navegador completa con Cookies y Tokens.
    """
    import requests
    import json
    import re
    import time
    from urllib.parse import quote
    
    print("🕷️ Iniciando Scraping Manual de Google Trends...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Referer': 'https://trends.google.com/',
        'Upgrade-Insecure-Requests': '1'
    })
    
    try:
        # PASO 1: Visitar la home para obtener Cookies iniciales (NID, etc)
        print("🕷️ Paso 1: Obteniendo cookies base...")
        resp_home = session.get('https://trends.google.com/trends/?geo=' + geo)
        if resp_home.status_code != 200:
            raise Exception(f"Error cargando home: {resp_home.status_code}")
            
        # PASO 2: Obtener el TOKEN de exploración
        print("🕷️ Paso 2: Obteniendo tokens de widget...")
        keyword = keywords[0]
        
        # Usar el time_range que viene de la app directamente
        # La app envía formatos estándar de Trends: "now 7-d", "today 1-m", "today 12-m", "today 5-y"
        time_param = time_range
        
        explore_url = 'https://trends.google.com/trends/api/explore'
        params = {
            'hl': 'es',
            'tz': '300',
            'req': json.dumps({
                "comparisonItem": [{"keyword": keyword, "geo": geo, "time": time_param}],
                "category": 0,
                "property": ""
            }),
            'tz': '300'
        }
        
        resp_explore = session.get(explore_url, params=params)
        content = resp_explore.text
        
        # Limpiar el prefijo de seguridad de Google (puede variar)
        # Buscamos el primer '{' para empezar el JSON
        first_brace = content.find('{')
        if first_brace != -1:
            content = content[first_brace:]
        else:
             print(f"⚠️ No se encontró JSON válido en: {content[:100]}")
            
        try:
            data_explore = json.loads(content)
        except json.JSONDecodeError:
            print(f"❌ Error decodificando JSON. Contenido recibido (primeros 500 chars):\n{content[:500]}")
            raise Exception("Google Trends devolvió una respuesta no válida (posible bloqueo)")
        widgets = data_explore.get('widgets', [])
        
        # Buscar el widget de "Interest by subregion" (o CITY/DMA)
        region_token = None
        timeline_token = None
        
        for widget in widgets:
            if widget.get('id') == 'GEO_MAP':
                region_token = widget.get('token')
                region_request = widget.get('request')
            if widget.get('id') == 'TIMESERIES':
                timeline_token = widget.get('token')
                timeline_request = widget.get('request')
                
        if not region_token:
            raise Exception("No se encontró token de región")
            
        # PASO 3: Pedir los datos de región usando el token
        print(f"🕷️ Paso 3: Descargando datos de región ({resolution})...")
        
        # Ajustar resolución en el request
        region_resolution = 'COUNTRY'
        if resolution == 'DMA': region_resolution = 'DMA'
        elif resolution == 'CITY': region_resolution = 'CITY'
        elif resolution == 'REGION': region_resolution = 'REGION'
        
        region_request['resolution'] = region_resolution
        region_request['includeLowSearchVolumeGeos'] = True # TRUE para tener todas las ubicaciones en el CSV
        
        region_url = 'https://trends.google.com/trends/api/widgetdata/comparedgeo'
        region_params = {
            'hl': 'es',
            'tz': '300',
            'req': json.dumps(region_request),
            'token': region_token,
            'locale': 'es'
        }
        
        resp_region = session.get(region_url, params=region_params)
        region_content = resp_region.text
        
        # Limpiar prefijo
        first_brace = region_content.find('{')
        if first_brace != -1:
            region_content = region_content[first_brace:]
            
        region_json = json.loads(region_content)
        
        # Procesar datos de región
        region_data = []
        if 'default' in region_json and 'geoMapData' in region_json['default']:
            for item in region_json['default']['geoMapData']:
                if item.get('hasData') and item.get('value'):
                    region_data.append({
                        'geoName': item.get('geoName'),
                        'value': item['value'][0], # Valor del primer keyword
                        'geoCode': item.get('geoCode')
                    })
        
        # PASO 4: Pedir datos de timeline
        print("🕷️ Paso 4: Descargando timeline...")
        timeline_data = []
        if timeline_token:
            timeline_url = 'https://trends.google.com/trends/api/widgetdata/multiline'
            timeline_params = {
                'hl': 'es',
                'tz': '300',
                'req': json.dumps(timeline_request),
                'token': timeline_token,
                'locale': 'es'
            }
            resp_timeline = session.get(timeline_url, params=timeline_params)
            timeline_content = resp_timeline.text
            
            # Limpiar prefijo
            first_brace = timeline_content.find('{')
            if first_brace != -1:
                timeline_content = timeline_content[first_brace:]
            
            timeline_json = json.loads(timeline_content)
            if 'default' in timeline_json and 'timelineData' in timeline_json['default']:
                for item in timeline_json['default']['timelineData']:
                    if item.get('hasData') and item.get('value'):
                        timeline_data.append({
                            'date': item.get('formattedTime'), # O formattedAxisTime
                            'value': item['value'][0]
                        })

        print(f"✅ Scraping exitoso: {len(region_data)} regiones encontradas")
        
        return {
            'timelineData': timeline_data,
            'interestByRegion': region_data,
            'relatedQueries': [], # Simplificado por ahora
            'source': 'pytrends' # Usamos el mismo identificador para el badge azul
        }
        
    except Exception as e:
        print(f"❌ Error en Scraping Manual: {str(e)}")
        raise e # Re-lanzar para que el fallback lo capture
