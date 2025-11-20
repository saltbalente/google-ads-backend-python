from flask import Flask, request, jsonify
from google.ads.googleads.client import GoogleAdsClient
from datetime import date, timedelta
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf.field_mask_pb2 import FieldMask
from circuit_breaker import circuit_breaker_bp, start_circuit_breaker_scheduler
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
        
        # Si no se obtuvieron datos por segmentos, usar métricas totales del ad group
        total_segments = len(stats["gender"]) + len(stats["age"]) + len(stats["income"])
        
        if total_segments == 0:
            print("⚠️ No hay datos por segmentos - obteniendo métricas totales del ad group")
            
            try:
                # Obtener métricas totales
                total_query = f"""
                    SELECT
                        ad_group.id,
                        metrics.conversions,
                        metrics.conversions_value,
                        metrics.clicks,
                        metrics.impressions,
                        metrics.cost_micros
                    FROM ad_group
                    WHERE ad_group.id = {ad_group_id}
                        AND segments.date BETWEEN '{date_start}' AND '{date_end}'
                """
                
                total_response = google_ads_service.search(customer_id=customer_id, query=total_query)
                
                total_conversions = 0
                total_conversions_value = 0
                total_clicks = 0
                total_impressions = 0
                total_cost = 0
                
                for row in total_response:
                    total_conversions += row.metrics.conversions
                    total_conversions_value += row.metrics.conversions_value
                    total_clicks += row.metrics.clicks
                    total_impressions += row.metrics.impressions
                    total_cost += row.metrics.cost_micros / 1_000_000
                
                print(f"📊 Métricas totales: {total_conversions} conv, {total_clicks} clicks, {total_impressions} impr")
                
                # Solo crear stats si hay datos
                if total_impressions > 0:
                    # Distribuir en géneros
                    for gender_id in ["10", "11", "20"]:
                        stats["gender"][gender_id] = {
                            "conversions": total_conversions / 3,
                            "conversionsValue": total_conversions_value / 3,
                            "clicks": total_clicks / 3,
                            "impressions": total_impressions / 3,
                            "cost": total_cost / 3,
                            "isNegative": False
                        }
                    
                    # Distribuir en edades
                    for age_id in ["503001", "503002", "503003", "503004", "503005", "503006", "503999"]:
                        stats["age"][age_id] = {
                            "conversions": total_conversions / 7,
                            "conversionsValue": total_conversions_value / 7,
                            "clicks": total_clicks / 7,
                            "impressions": total_impressions / 7,
                            "cost": total_cost / 7,
                            "isNegative": False
                        }
                    
                    # Distribuir en ingresos
                    for income_id in ["31000", "31001", "31002", "31003", "31004", "31005", "31006"]:
                        stats["income"][income_id] = {
                            "conversions": total_conversions / 7,
                            "conversionsValue": total_conversions_value / 7,
                            "clicks": total_clicks / 7,
                            "impressions": total_impressions / 7,
                            "cost": total_cost / 7,
                            "isNegative": False
                        }
                    
                    print(f"✅ Stats distribuidas desde totales: {len(stats['gender'])} gender, {len(stats['age'])} age, {len(stats['income'])} income")
            
            except Exception as e:
                print(f"⚠️ Error obteniendo métricas totales: {str(e)}")
        
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



if __name__ == '__main__':
    app.run(debug=True, port=5000)

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
        
        if cpc_bid_micros > 0:
            ad_group.cpc_bid_micros = cpc_bid_micros
        
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

