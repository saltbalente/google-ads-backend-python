"""
ALTERNATIVA CORREGIDA: Usar ad_group_criterion en lugar de segments.*

Este código debería reemplazar la función get_demographic_stats() si segments.*
continúa devolviendo 0s.

ad_group_criterion obtiene datos de los criterios demográficos configurados
en el ad group, lo cual es más confiable que segments.* que puede estar vacío.
"""

@app.route('/api/demographics/stats', methods=['POST', 'OPTIONS'])
def get_demographic_stats():
    """Obtiene estadísticas REALES usando ad_group_criterion
    
    VERSIÓN ALTERNATIVA: Usa ad_group_criterion en lugar de segments.*
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
        
        print(f"📊 [CRITERION] Loading demographic stats for AdGroup {ad_group_id}, period: {date_start} to {date_end}")
        
        stats = {
            "gender": {},
            "age": {},
            "income": {}
        }
        
        # Query ÚNICA que obtiene TODOS los criterios demográficos de una vez
        try:
            criterion_query = f"""
                SELECT
                    ad_group_criterion.criterion_id,
                    ad_group_criterion.type,
                    ad_group_criterion.status,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.cost_micros
                FROM ad_group_criterion
                WHERE ad_group.id = {ad_group_id}
                    AND ad_group_criterion.type IN ('GENDER', 'AGE_RANGE', 'INCOME_RANGE')
                    AND segments.date BETWEEN '{date_start}' AND '{date_end}'
            """
            
            print(f"🔍 Executing criterion query...")
            criterion_response = google_ads_service.search(customer_id=customer_id, query=criterion_query)
            
            # Acumuladores por tipo
            gender_accumulator = {}
            age_accumulator = {}
            income_accumulator = {}
            
            row_count = 0
            
            for row in criterion_response:
                row_count += 1
                criterion_id = str(row.ad_group_criterion.criterion_id)
                criterion_type = row.ad_group_criterion.type.name
                status = row.ad_group_criterion.status.name
                
                conversions = row.metrics.conversions
                clicks = row.metrics.clicks
                impressions = row.metrics.impressions
                cost = row.metrics.cost_micros / 1_000_000.0
                
                print(f"  Row {row_count}: type={criterion_type}, id={criterion_id}, status={status}, clicks={clicks}, conv={conversions}")
                
                # Crear entrada si no existe
                base_data = {
                    "conversions": 0,
                    "conversionsValue": 0,
                    "clicks": 0,
                    "impressions": 0,
                    "cost": 0
                }
                
                # Acumular según el tipo
                if criterion_type == "GENDER":
                    if criterion_id not in gender_accumulator:
                        gender_accumulator[criterion_id] = base_data.copy()
                    gender_accumulator[criterion_id]["conversions"] += conversions
                    gender_accumulator[criterion_id]["conversionsValue"] += row.metrics.conversions_value
                    gender_accumulator[criterion_id]["clicks"] += clicks
                    gender_accumulator[criterion_id]["impressions"] += impressions
                    gender_accumulator[criterion_id]["cost"] += cost
                
                elif criterion_type == "AGE_RANGE":
                    if criterion_id not in age_accumulator:
                        age_accumulator[criterion_id] = base_data.copy()
                    age_accumulator[criterion_id]["conversions"] += conversions
                    age_accumulator[criterion_id]["conversionsValue"] += row.metrics.conversions_value
                    age_accumulator[criterion_id]["clicks"] += clicks
                    age_accumulator[criterion_id]["impressions"] += impressions
                    age_accumulator[criterion_id]["cost"] += cost
                
                elif criterion_type == "INCOME_RANGE":
                    if criterion_id not in income_accumulator:
                        income_accumulator[criterion_id] = base_data.copy()
                    income_accumulator[criterion_id]["conversions"] += conversions
                    income_accumulator[criterion_id]["conversionsValue"] += row.metrics.conversions_value
                    income_accumulator[criterion_id]["clicks"] += clicks
                    income_accumulator[criterion_id]["impressions"] += impressions
                    income_accumulator[criterion_id]["cost"] += cost
            
            print(f"📊 Criterion query returned {row_count} rows total")
            print(f"📊 Gender: {len(gender_accumulator)}, Age: {len(age_accumulator)}, Income: {len(income_accumulator)}")
            
            # Convertir a formato final para GÉNERO
            for criterion_id, data in gender_accumulator.items():
                stats["gender"][criterion_id] = {
                    "conversions": float(data["conversions"]),
                    "conversionsValue": float(data["conversionsValue"]),
                    "clicks": float(data["clicks"]),
                    "impressions": float(data["impressions"]),
                    "cost": float(data["cost"]),
                    "isNegative": False
                }
                print(f"  ✅ Gender {criterion_id}: Conv={data['conversions']}, Clicks={data['clicks']}")
            
            # Llenar con 0s los IDs estándar de género que no tienen datos
            for gender_id in ["10", "11", "20"]:
                if gender_id not in stats["gender"]:
                    stats["gender"][gender_id] = {
                        "conversions": 0.0,
                        "conversionsValue": 0.0,
                        "clicks": 0.0,
                        "impressions": 0.0,
                        "cost": 0.0,
                        "isNegative": False
                    }
            
            # Convertir a formato final para EDAD
            for criterion_id, data in age_accumulator.items():
                stats["age"][criterion_id] = {
                    "conversions": float(data["conversions"]),
                    "conversionsValue": float(data["conversionsValue"]),
                    "clicks": float(data["clicks"]),
                    "impressions": float(data["impressions"]),
                    "cost": float(data["cost"]),
                    "isNegative": False
                }
                print(f"  ✅ Age {criterion_id}: Conv={data['conversions']}, Clicks={data['clicks']}")
            
            # Llenar con 0s los IDs estándar de edad que no tienen datos
            for age_id in ["503001", "503002", "503003", "503004", "503005", "503006", "503999"]:
                if age_id not in stats["age"]:
                    stats["age"][age_id] = {
                        "conversions": 0.0,
                        "conversionsValue": 0.0,
                        "clicks": 0.0,
                        "impressions": 0.0,
                        "cost": 0.0,
                        "isNegative": False
                    }
            
            # Convertir a formato final para INGRESO
            for criterion_id, data in income_accumulator.items():
                stats["income"][criterion_id] = {
                    "conversions": float(data["conversions"]),
                    "conversionsValue": float(data["conversionsValue"]),
                    "clicks": float(data["clicks"]),
                    "impressions": float(data["impressions"]),
                    "cost": float(data["cost"]),
                    "isNegative": False
                }
                print(f"  ✅ Income {criterion_id}: Conv={data['conversions']}, Clicks={data['clicks']}")
            
            # Llenar con 0s los IDs estándar de ingreso que no tienen datos
            for income_id in ["31000", "31001", "31002", "31003", "31004", "31005", "31006"]:
                if income_id not in stats["income"]:
                    stats["income"][income_id] = {
                        "conversions": 0.0,
                        "conversionsValue": 0.0,
                        "clicks": 0.0,
                        "impressions": 0.0,
                        "cost": 0.0,
                        "isNegative": False
                    }
            
            print(f"✅ [CRITERION] Stats loaded successfully")
        
        except Exception as e:
            print(f"❌ Error loading criterion stats: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # En caso de error, llenar todo con 0s
            for gender_id in ["10", "11", "20"]:
                stats["gender"][gender_id] = {"conversions": 0.0, "conversionsValue": 0.0, "clicks": 0.0, "impressions": 0.0, "cost": 0.0, "isNegative": False}
            for age_id in ["503001", "503002", "503003", "503004", "503005", "503006", "503999"]:
                stats["age"][age_id] = {"conversions": 0.0, "conversionsValue": 0.0, "clicks": 0.0, "impressions": 0.0, "cost": 0.0, "isNegative": False}
            for income_id in ["31000", "31001", "31002", "31003", "31004", "31005", "31006"]:
                stats["income"][income_id] = {"conversions": 0.0, "conversionsValue": 0.0, "clicks": 0.0, "impressions": 0.0, "cost": 0.0, "isNegative": False}
        
        result = jsonify({
            "success": True,
            "stats": stats,
            "dateRange": {
                "start": date_start,
                "end": date_end,
                "days": int(days)
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
        
        print(f"❌ GoogleAdsException: {errors}")
        
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
        import traceback
        traceback.print_exc()
        
        result = jsonify({
            "success": False,
            "message": str(ex)
        }), 500
        
        result[0].headers.add('Access-Control-Allow-Origin', '*')
        return result
