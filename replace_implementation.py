#!/usr/bin/env python3
"""
Script para reemplazar la implementación de get_demographic_stats()
con la versión basada en ad_group_criterion
"""

import re

# Leer el archivo actual
with open('app.py', 'r') as f:
    content = f.read()

# Nuevo código a insertar
new_implementation = '''        data = request.json
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
        
        client = get_google_ads_client()
        google_ads_service = client.get_service("GoogleAdsService")
        
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(days))
        date_start = start_date.strftime("%Y-%m-%d")
        date_end = end_date.strftime("%Y-%m-%d")
        
        print(f"📊 [CRITERION] Loading demographic stats for AdGroup {ad_group_id}, period: {date_start} to {date_end}")
        
        stats = {"gender": {}, "age": {}, "income": {}}
        
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
            
            gender_acc = {}
            age_acc = {}
            income_acc = {}
            row_count = 0
            
            for row in criterion_response:
                row_count += 1
                criterion_id = str(row.ad_group_criterion.criterion_id)
                criterion_type = row.ad_group_criterion.type.name
                status = row.ad_group_criterion.status.name
                
                conv = row.metrics.conversions
                clicks = row.metrics.clicks
                impr = row.metrics.impressions
                cost = row.metrics.cost_micros / 1_000_000.0
                
                print(f"  Row {row_count}: type={criterion_type}, id={criterion_id}, status={status}, clicks={clicks}, conv={conv}")
                
                base_data = {"conversions": 0, "conversionsValue": 0, "clicks": 0, "impressions": 0, "cost": 0}
                
                if criterion_type == "GENDER":
                    if criterion_id not in gender_acc:
                        gender_acc[criterion_id] = base_data.copy()
                    gender_acc[criterion_id]["conversions"] += conv
                    gender_acc[criterion_id]["conversionsValue"] += row.metrics.conversions_value
                    gender_acc[criterion_id]["clicks"] += clicks
                    gender_acc[criterion_id]["impressions"] += impr
                    gender_acc[criterion_id]["cost"] += cost
                
                elif criterion_type == "AGE_RANGE":
                    if criterion_id not in age_acc:
                        age_acc[criterion_id] = base_data.copy()
                    age_acc[criterion_id]["conversions"] += conv
                    age_acc[criterion_id]["conversionsValue"] += row.metrics.conversions_value
                    age_acc[criterion_id]["clicks"] += clicks
                    age_acc[criterion_id]["impressions"] += impr
                    age_acc[criterion_id]["cost"] += cost
                
                elif criterion_type == "INCOME_RANGE":
                    if criterion_id not in income_acc:
                        income_acc[criterion_id] = base_data.copy()
                    income_acc[criterion_id]["conversions"] += conv
                    income_acc[criterion_id]["conversionsValue"] += row.metrics.conversions_value
                    income_acc[criterion_id]["clicks"] += clicks
                    income_acc[criterion_id]["impressions"] += impr
                    income_acc[criterion_id]["cost"] += cost
            
            print(f"📊 Criterion query returned {row_count} rows total")
            print(f"📊 Gender: {len(gender_acc)}, Age: {len(age_acc)}, Income: {len(income_acc)}")
            
            # Convert gender
            for criterion_id, data in gender_acc.items():
                stats["gender"][criterion_id] = {
                    "conversions": float(data["conversions"]),
                    "conversionsValue": float(data["conversionsValue"]),
                    "clicks": float(data["clicks"]),
                    "impressions": float(data["impressions"]),
                    "cost": float(data["cost"]),
                    "isNegative": False
                }
                print(f"  ✅ Gender {criterion_id}: Conv={data['conversions']}, Clicks={data['clicks']}")
            
            for gender_id in ["10", "11", "20"]:
                if gender_id not in stats["gender"]:
                    stats["gender"][gender_id] = {"conversions": 0.0, "conversionsValue": 0.0, "clicks": 0.0, "impressions": 0.0, "cost": 0.0, "isNegative": False}
            
            # Convert age
            for criterion_id, data in age_acc.items():
                stats["age"][criterion_id] = {
                    "conversions": float(data["conversions"]),
                    "conversionsValue": float(data["conversionsValue"]),
                    "clicks": float(data["clicks"]),
                    "impressions": float(data["impressions"]),
                    "cost": float(data["cost"]),
                    "isNegative": False
                }
                print(f"  ✅ Age {criterion_id}: Conv={data['conversions']}, Clicks={data['clicks']}")
            
            for age_id in ["503001", "503002", "503003", "503004", "503005", "503006", "503999"]:
                if age_id not in stats["age"]:
                    stats["age"][age_id] = {"conversions": 0.0, "conversionsValue": 0.0, "clicks": 0.0, "impressions": 0.0, "cost": 0.0, "isNegative": False}
            
            # Convert income
            for criterion_id, data in income_acc.items():
                stats["income"][criterion_id] = {
                    "conversions": float(data["conversions"]),
                    "conversionsValue": float(data["conversionsValue"]),
                    "clicks": float(data["clicks"]),
                    "impressions": float(data["impressions"]),
                    "cost": float(data["cost"]),
                    "isNegative": False
                }
                print(f"  ✅ Income {criterion_id}: Conv={data['conversions']}, Clicks={data['clicks']}")
            
            for income_id in ["31000", "31001", "31002", "31003", "31004", "31005", "31006"]:
                if income_id not in stats["income"]:
                    stats["income"][income_id] = {"conversions": 0.0, "conversionsValue": 0.0, "clicks": 0.0, "impressions": 0.0, "cost": 0.0, "isNegative": False}
            
            print(f"✅ [CRITERION] Stats loaded successfully")
        
        except Exception as e:
            print(f"❌ Error loading criterion stats: {str(e)}")
            import traceback
            traceback.print_exc()
            
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
                "days": days
            }
        })
        
        result.headers.add('Access-Control-Allow-Origin', '*')
        return result
        
    '''

# Patron para encontrar y reemplazar
# Desde "try:" después de "def get_demographic_stats():"  
# Hasta antes de "except GoogleAdsException"
pattern = r'(def get_demographic_stats\(\):.*?""".*?    )(try:.*?)(    except GoogleAdsException)'

def replacer(match):
    return match.group(1) + new_implementation + match.group(3)

new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)

# Escribir el nuevo archivo
with open('app.py', 'w') as f:
    f.write(new_content)

print("✅ Archivo app.py actualizado correctamente")
print("📊 Nuevo código usa ad_group_criterion en lugar de segments.*")
