from flask import Flask, request, jsonify
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from dotenv import load_dotenv
import os

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
        age_ranges = []
        household_incomes = []
        
        for row in response:
            criterion = row.ad_group_criterion
            
            # Solo criterios positivos (no negativos)
            if criterion.negative:
                continue
            
            if criterion.type_.name == 'GENDER':
                gender_id = str(criterion.gender.type.value)
                if gender_id not in genders:
                    genders.append(gender_id)
            
            elif criterion.type_.name == 'AGE_RANGE':
                age_id = str(criterion.age_range.type.value)
                if age_id not in age_ranges:
                    age_ranges.append(age_id)
            
            elif criterion.type_.name == 'INCOME_RANGE':
                income_id = str(criterion.income_range.type.value)
                if income_id not in household_incomes:
                    household_incomes.append(income_id)
        
        result = jsonify({
            "success": True,
            "message": "Configuración demográfica obtenida",
            "demographics": {
                "genders": genders,
                "ageRanges": age_ranges,
                "householdIncomes": household_incomes
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
        
        # Recibir estados de todos los criterios (true = incluir, false = excluir)
        gender_states = data.get('genderStates', {})  # {"10": true, "11": false, "20": true}
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
        
        for gender_id, is_enabled in gender_states.items():
            if str(gender_id) not in gender_map:
                continue
            
            operation = client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = ad_group_path
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.negative = not is_enabled  # true = incluir (negative=False), false = excluir (negative=True)
            criterion.gender.type_ = gender_map[str(gender_id)]
            operations.append(operation)
            
            if is_enabled:
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
        
        for age_id, is_enabled in age_states.items():
            if str(age_id) not in age_map:
                continue
            
            operation = client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = ad_group_path
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.negative = not is_enabled  # true = incluir (negative=False), false = excluir (negative=True)
            criterion.age_range.type_ = age_map[str(age_id)]
            operations.append(operation)
            
            if is_enabled:
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
        
        for income_id, is_enabled in income_states.items():
            if str(income_id) not in income_map:
                continue
            
            operation = client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = ad_group_path
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.negative = not is_enabled  # true = incluir (negative=False), false = excluir (negative=True)
            criterion.income_range.type_ = income_map[str(income_id)]
            operations.append(operation)
            
            if is_enabled:
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
                "error_code": error.error_code.to_json() if hasattr(error, 'error_code') else None
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
                "error_code": error.error_code.to_json() if hasattr(error, 'error_code') else None
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
                "error_code": error.error_code.to_json() if hasattr(error, 'error_code') else None,
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
        days = data.get('days', 7)  # Por defecto 7 días
        
        if not all([customer_id, ad_group_id]):
            return jsonify({
                "success": False,
                "message": "Faltan customerId o adGroupId"
            }), 400
        
        # Crear cliente
        client = get_google_ads_client()
        google_ads_service = client.get_service("GoogleAdsService")
        
        # Calcular fecha de inicio
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        date_start = start_date.strftime("%Y-%m-%d")
        date_end = end_date.strftime("%Y-%m-%d")
        
        # Organizar estadísticas por tipo
        stats = {
            "gender": {},
            "age": {},
            "income": {}
        }
        
        print(f"📊 Obteniendo stats demográficas reales del ad group {ad_group_id}")
        
        # Query 1: Estadísticas por GÉNERO usando segments.ad_network_type
        try:
            gender_query = f"""
                SELECT
                    ad_group.id,
                    segments.gender,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros
                FROM ad_group
                WHERE ad_group.id = {ad_group_id}
                    AND segments.date BETWEEN '{date_start}' AND '{date_end}'
                    AND segments.gender != 'UNSPECIFIED'
            """
            
            gender_response = google_ads_service.search(customer_id=customer_id, query=gender_query)
            
            for row in gender_response:
                gender_enum = row.segments.gender
                gender_id = str(gender_enum.value)  # Convertir enum a valor numérico
                
                print(f"   🔹 Gender segment: {gender_enum.name} (ID: {gender_id})")
                
                if gender_id not in stats["gender"]:
                    stats["gender"][gender_id] = {
                        "conversions": 0,
                        "conversionsValue": 0,
                        "clicks": 0,
                        "impressions": 0,
                        "cost": 0,
                        "isNegative": False
                    }
                
                stats["gender"][gender_id]["conversions"] += row.metrics.conversions
                stats["gender"][gender_id]["conversionsValue"] += row.metrics.conversions_value
                stats["gender"][gender_id]["clicks"] += row.metrics.clicks
                stats["gender"][gender_id]["impressions"] += row.metrics.impressions
                stats["gender"][gender_id]["cost"] += row.metrics.cost_micros / 1_000_000
                
                print(f"      Conv: {row.metrics.conversions}, Clicks: {row.metrics.clicks}")
            
            print(f"✅ Gender stats obtenidas: {len(stats['gender'])} segmentos")
        except Exception as e:
            print(f"⚠️ Error obteniendo gender stats: {str(e)}")
        
        # Query 2: Estadísticas por EDAD
        try:
            age_query = f"""
                SELECT
                    ad_group.id,
                    segments.age_range,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros
                FROM ad_group
                WHERE ad_group.id = {ad_group_id}
                    AND segments.date BETWEEN '{date_start}' AND '{date_end}'
                    AND segments.age_range != 'UNSPECIFIED'
            """
            
            age_response = google_ads_service.search(customer_id=customer_id, query=age_query)
            
            for row in age_response:
                age_enum = row.segments.age_range
                age_id = str(age_enum.value)
                
                print(f"   🔹 Age segment: {age_enum.name} (ID: {age_id})")
                
                if age_id not in stats["age"]:
                    stats["age"][age_id] = {
                        "conversions": 0,
                        "conversionsValue": 0,
                        "clicks": 0,
                        "impressions": 0,
                        "cost": 0,
                        "isNegative": False
                    }
                
                stats["age"][age_id]["conversions"] += row.metrics.conversions
                stats["age"][age_id]["conversionsValue"] += row.metrics.conversions_value
                stats["age"][age_id]["clicks"] += row.metrics.clicks
                stats["age"][age_id]["impressions"] += row.metrics.impressions
                stats["age"][age_id]["cost"] += row.metrics.cost_micros / 1_000_000
                
                print(f"      Conv: {row.metrics.conversions}, Clicks: {row.metrics.clicks}")
            
            print(f"✅ Age stats obtenidas: {len(stats['age'])} segmentos")
        except Exception as e:
            print(f"⚠️ Error obteniendo age stats: {str(e)}")
        
        # Query 3: Estadísticas por INGRESO (Household Income)
        try:
            income_query = f"""
                SELECT
                    ad_group.id,
                    segments.household_income,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros
                FROM ad_group
                WHERE ad_group.id = {ad_group_id}
                    AND segments.date BETWEEN '{date_start}' AND '{date_end}'
                    AND segments.household_income != 'UNSPECIFIED'
            """
            
            income_response = google_ads_service.search(customer_id=customer_id, query=income_query)
            
            for row in income_response:
                income_enum = row.segments.household_income
                income_id = str(income_enum.value)
                
                print(f"   🔹 Income segment: {income_enum.name} (ID: {income_id})")
                
                if income_id not in stats["income"]:
                    stats["income"][income_id] = {
                        "conversions": 0,
                        "conversionsValue": 0,
                        "clicks": 0,
                        "impressions": 0,
                        "cost": 0,
                        "isNegative": False
                    }
                
                stats["income"][income_id]["conversions"] += row.metrics.conversions
                stats["income"][income_id]["conversionsValue"] += row.metrics.conversions_value
                stats["income"][income_id]["clicks"] += row.metrics.clicks
                stats["income"][income_id]["impressions"] += row.metrics.impressions
                stats["income"][income_id]["cost"] += row.metrics.cost_micros / 1_000_000
                
                print(f"      Conv: {row.metrics.conversions}, Clicks: {row.metrics.clicks}")
            
            print(f"✅ Income stats obtenidas: {len(stats['income'])} segmentos")
        except Exception as e:
            print(f"⚠️ Error obteniendo income stats: {str(e)}")
        
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
