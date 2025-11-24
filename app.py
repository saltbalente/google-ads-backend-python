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

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

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
        client = get_google_ads_client()
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
        client = get_google_ads_client()
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
        client = get_google_ads_client()
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
        client = get_google_ads_client()
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
        client = get_google_ads_client()
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
        client = get_google_ads_client()
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
        client = get_google_ads_client()
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
        client = get_google_ads_client()
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
    else:
        svc = ga_client.get_service("CampaignAssetService")
        op = ga_client.get_type("CampaignAssetOperation")
        create = op.create
        create.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
        create.asset = asset_resource_name
        create.field_type = field_type_enum_value
        svc.mutate_campaign_assets(customer_id=customer_id, operations=[op])

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
        if not all([customer_id, campaign_id, fmt, image_b64]):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"}), 400
            res[0].headers.add('Access-Control-Allow-Origin', '*')
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
        ga = get_google_ads_client()
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
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors, "details": details}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
        return res

@app.route('/api/campaigns/top-final-urls', methods=['POST', 'OPTIONS'])
def top_campaign_final_urls():
    if request.method == 'OPTIONS':
        return cors_preflight_ok()
    try:
        data = request.get_json()
        customer_id = data.get('customerId', '').replace('-', '')
        if not customer_id:
            res = jsonify({"success": False, "message": "customerId requerido"}), 400
            res[0].headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_google_ads_client()
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
            result = jsonify({"success": True, "finalUrls": []}), 200
            result[0].headers.add('Access-Control-Allow-Origin', '*')
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
        result = jsonify({"success": True, "campaignId": str(top_campaign_id), "finalUrls": urls}), 200
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
    except GoogleAdsException as ex:
        errors = [error.message for error in ex.failure.errors]
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
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
            res = jsonify({"success": False, "message": "customerId requerido"}), 400
            res[0].headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_google_ads_client()
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
            res = jsonify({"success": False, "message": "AI provider response unavailable", "details": detail}), 500
            res[0].headers.add('Access-Control-Allow-Origin', '*')
            return res
        for i in range(min(count, len(candidates))):
            item = candidates[i]
            title = clamp(str(item.get('title','')).strip(), 25)
            d1 = clamp(str(item.get('description1','')).strip(), 35)
            d2 = clamp(str(item.get('description2','')).strip(), 35)
            base = base_url or 'https://example.com'
            url = base.split('#')[0] + '#' + slugify(title)
            sitelinks.append({"title": title, "description1": d1, "description2": d2, "url": url})
        result = jsonify({"success": True, "sitelinks": sitelinks}), 200
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
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
        if not all([customer_id, campaign_id, text, final_url]):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"}), 400
            res[0].headers.add('Access-Control-Allow-Origin', '*')
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
        ga = get_google_ads_client()
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
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors, "details": details}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
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
        final_url = data.get('finalUrl', '')
        if not all([customer_id, campaign_id]) or not p:
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"}), 400
            res[0].headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_google_ads_client()
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
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
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
        if not all([customer_id, campaign_id, cc, phone]):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"}), 400
            res[0].headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_google_ads_client()
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
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
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
        if not all([customer_id, campaign_id]) or (not text and not texts):
            res = jsonify({"success": False, "message": "Parámetros requeridos faltantes"}), 400
            res[0].headers.add('Access-Control-Allow-Origin', '*')
            return res
        ga = get_google_ads_client()
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
        res = jsonify({"success": False, "message": "Google Ads API Error", "errors": errors}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
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
        res = jsonify({"success": False, "message": str(ex)}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
        return res
    except Exception as ex:
        res = jsonify({"success": False, "message": str(ex)}), 500
        res[0].headers.add('Access-Control-Allow-Origin', '*')
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
            }), 400
            result[0].headers.add('Access-Control-Allow-Origin', '*')
            return result
        
        # Crear cliente
        client = get_google_ads_client()
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
        client = get_google_ads_client()
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
        client = get_google_ads_client()
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
        
        client = get_google_ads_client()
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
        
        client = get_google_ads_client()
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
        
        client = get_google_ads_client()
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
        
        client = get_google_ads_client()
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
        
        client = get_google_ads_client()
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
        
        client = get_google_ads_client()
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
        
        client = get_google_ads_client()
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
if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    app.run(debug=True, port=port)
