#!/usr/bin/env python3
"""
🔬 TRINITY DIAGNOSTIC: Google Ads Conversion Data Analysis
============================================================
Este script prueba directamente la API de Google Ads para identificar
EXACTAMENTE qué datos de conversiones están disponibles.

Ejecutar con:
    python diagnostic_conversions.py

Requisitos:
    - Variable de entorno GOOGLE_ADS_REFRESH_TOKEN
    - Archivo .env con configuración
"""

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Tu developer token de Google Ads
DEVELOPER_TOKEN = "Kqg431In6DxoZnSMJk0hQg"

# OAuth2 credentials - desde .env
CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "82393641971-edkinpiigpprkbdi0dtnalem8ndo5c1j.apps.googleusercontent.com")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "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")
REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")

# Account IDs (sin guiones)
# Login Customer ID es el MCC
LOGIN_CUSTOMER_ID = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "8531174172")

# Customer ID será proporcionado como argumento o usaremos el MCC para listar cuentas
CUSTOMER_ID = None  # Se obtendrá dinámicamente

# Fecha range para análisis
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=30)
START_STR = START_DATE.strftime("%Y-%m-%d")
END_STR = END_DATE.strftime("%Y-%m-%d")

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def get_access_token():
    """Obtener access token fresco usando refresh token"""
    print("\n🔑 Obteniendo access token...")
    
    if not REFRESH_TOKEN:
        print("❌ ERROR: GOOGLE_ADS_REFRESH_TOKEN no está configurado")
        print("   Configúralo en .env o como variable de entorno")
        return None
    
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"✅ Access token obtenido: {token[:20]}...")
            return token
        else:
            print(f"❌ Error obteniendo token: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return None


def list_accessible_accounts(access_token):
    """Listar todas las cuentas accesibles bajo el MCC"""
    print("\n📋 Listando cuentas accesibles...")
    
    url = f"https://googleads.googleapis.com/v22/customers/{LOGIN_CUSTOMER_ID}/googleAds:search"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": DEVELOPER_TOKEN,
        "login-customer-id": LOGIN_CUSTOMER_ID,
        "Content-Type": "application/json"
    }
    
    # Query para listar cuentas hijas del MCC
    query = """
        SELECT
          customer_client.client_customer,
          customer_client.descriptive_name,
          customer_client.id,
          customer_client.status
        FROM customer_client
        WHERE customer_client.status = 'ENABLED'
        AND customer_client.manager = FALSE
    """
    
    try:
        response = requests.post(url, headers=headers, json={"query": query})
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            accounts = []
            print(f"\n✅ Encontradas {len(results)} cuentas:")
            print("-" * 60)
            
            for i, row in enumerate(results):
                client = row.get("customerClient", {})
                account_id = client.get("id", "N/A")
                name = client.get("descriptiveName", "Sin nombre")
                status = client.get("status", "N/A")
                
                accounts.append({
                    "id": account_id,
                    "name": name,
                    "status": status
                })
                
                print(f"  {i+1}. [{account_id}] {name} ({status})")
            
            return accounts
        else:
            print(f"❌ Error listando cuentas: {response.status_code}")
            print(f"   {response.text[:300]}")
            return []
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return []


def execute_query(query, access_token, customer_id, login_customer_id):
    """Ejecutar query GAQL y retornar resultados"""
    url = f"https://googleads.googleapis.com/v22/customers/{customer_id}/googleAds:search"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": DEVELOPER_TOKEN,
        "login-customer-id": login_customer_id,
        "Content-Type": "application/json"
    }
    
    payload = {"query": query}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            return {"success": True, "results": results, "count": len(results)}
        else:
            # Extraer mensaje de error más detallado
            error_msg = response.text[:500]
            try:
                error_json = response.json()
                if "error" in error_json and "details" in error_json["error"]:
                    for detail in error_json["error"]["details"]:
                        if "errors" in detail:
                            for err in detail["errors"]:
                                error_code = err.get("errorCode", {})
                                msg = err.get("message", "")
                                error_msg = f"{error_code} - {msg}"
                                break
            except:
                pass
            return {"success": False, "error": error_msg, "status": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def print_separator(title):
    """Imprimir separador visual"""
    print("\n" + "=" * 70)
    print(f"📊 {title}")
    print("=" * 70)


def print_sample_data(results, max_samples=5):
    """Imprimir muestra de datos"""
    if not results:
        print("   (Sin datos)")
        return
    
    for i, row in enumerate(results[:max_samples]):
        print(f"\n   📌 Row {i+1}:")
        print(f"      {json.dumps(row, indent=6, default=str)}")
    
    if len(results) > max_samples:
        print(f"\n   ... y {len(results) - max_samples} filas más")


# ============================================================
# QUERIES DE DIAGNÓSTICO
# ============================================================

DIAGNOSTIC_QUERIES = {
    "1_CUSTOMER_LEVEL_DAILY": {
        "description": "Conversiones a nivel CUENTA por DÍA (el más confiable)",
        "query": f"""
            SELECT
              segments.date,
              metrics.conversions,
              metrics.all_conversions,
              metrics.conversions_value,
              metrics.cost_micros,
              metrics.clicks,
              metrics.impressions
            FROM customer
            WHERE segments.date BETWEEN '{START_STR}' AND '{END_STR}'
            ORDER BY segments.date DESC
        """
    },
    
    "2_CAMPAIGN_LEVEL_DAILY": {
        "description": "Conversiones por CAMPAÑA por DÍA",
        "query": f"""
            SELECT
              campaign.id,
              campaign.name,
              segments.date,
              metrics.conversions,
              metrics.cost_micros,
              metrics.clicks
            FROM campaign
            WHERE segments.date BETWEEN '{START_STR}' AND '{END_STR}'
            AND campaign.status = 'ENABLED'
            ORDER BY metrics.conversions DESC
            LIMIT 50
        """
    },
    
    "3_CAMPAIGN_WITH_HOUR": {
        "description": "Conversiones por CAMPAÑA con segmento HORA",
        "query": f"""
            SELECT
              campaign.name,
              segments.hour,
              segments.day_of_week,
              metrics.conversions,
              metrics.cost_micros
            FROM campaign
            WHERE segments.date BETWEEN '{START_STR}' AND '{END_STR}'
            AND campaign.status = 'ENABLED'
            LIMIT 100
        """
    },
    
    "4_AD_GROUP_LEVEL": {
        "description": "Conversiones por GRUPO DE ANUNCIOS",
        "query": f"""
            SELECT
              campaign.name,
              ad_group.id,
              ad_group.name,
              metrics.conversions,
              metrics.cost_micros,
              metrics.clicks
            FROM ad_group
            WHERE segments.date BETWEEN '{START_STR}' AND '{END_STR}'
            AND ad_group.status = 'ENABLED'
            ORDER BY metrics.conversions DESC
            LIMIT 50
        """
    },
    
    "5_KEYWORD_VIEW": {
        "description": "Conversiones por KEYWORD (sin segmento hora)",
        "query": f"""
            SELECT
              campaign.name,
              ad_group.name,
              ad_group_criterion.keyword.text,
              ad_group_criterion.keyword.match_type,
              metrics.conversions,
              metrics.cost_micros,
              metrics.clicks,
              metrics.impressions
            FROM keyword_view
            WHERE segments.date BETWEEN '{START_STR}' AND '{END_STR}'
            ORDER BY metrics.conversions DESC
            LIMIT 50
        """
    },
    
    "6_SEARCH_TERMS": {
        "description": "Términos de búsqueda con conversiones",
        "query": f"""
            SELECT
              campaign.name,
              segments.search_term_match_type,
              search_term_view.search_term,
              metrics.conversions,
              metrics.cost_micros,
              metrics.clicks
            FROM search_term_view
            WHERE segments.date BETWEEN '{START_STR}' AND '{END_STR}'
            ORDER BY metrics.conversions DESC
            LIMIT 50
        """
    },
    
    "7_DEVICE_SEGMENT": {
        "description": "Conversiones por DISPOSITIVO",
        "query": f"""
            SELECT
              segments.device,
              metrics.conversions,
              metrics.cost_micros,
              metrics.clicks,
              metrics.impressions
            FROM campaign
            WHERE segments.date BETWEEN '{START_STR}' AND '{END_STR}'
            AND campaign.status = 'ENABLED'
        """
    },
    
    "8_CONVERSION_ACTIONS": {
        "description": "Tipos de CONVERSIÓN configurados en la cuenta",
        "query": """
            SELECT
              conversion_action.id,
              conversion_action.name,
              conversion_action.status,
              conversion_action.type,
              conversion_action.category,
              conversion_action.counting_type
            FROM conversion_action
            WHERE conversion_action.status = 'ENABLED'
        """
    },
    
    "9_CONVERSION_BY_ACTION": {
        "description": "Conversiones desglosadas por TIPO de conversión",
        "query": f"""
            SELECT
              segments.conversion_action_name,
              segments.conversion_action_category,
              segments.date,
              metrics.conversions,
              metrics.conversions_value
            FROM customer
            WHERE segments.date BETWEEN '{START_STR}' AND '{END_STR}'
            ORDER BY metrics.conversions DESC
            LIMIT 50
        """
    },
    
    "10_ALL_CONVERSIONS_CHECK": {
        "description": "Comparar conversions vs ALL_conversions",
        "query": f"""
            SELECT
              segments.date,
              metrics.conversions,
              metrics.all_conversions,
              metrics.view_through_conversions,
              metrics.cross_device_conversions
            FROM customer
            WHERE segments.date BETWEEN '{START_STR}' AND '{END_STR}'
            ORDER BY segments.date DESC
        """
    }
}


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    print("\n" + "🔬" * 35)
    print("   TRINITY DIAGNOSTIC: Google Ads Conversion Analysis")
    print("🔬" * 35)
    
    print(f"\n📅 Período de análisis: {START_STR} a {END_STR}")
    print(f"🔐 Login Customer ID (MCC): {LOGIN_CUSTOMER_ID}")
    
    # Obtener access token
    access_token = get_access_token()
    if not access_token:
        print("\n❌ No se pudo obtener access token. Abortando.")
        return
    
    # Listar cuentas disponibles
    accounts = list_accessible_accounts(access_token)
    
    if not accounts:
        print("\n❌ No se encontraron cuentas accesibles. Abortando.")
        return
    
    # Seleccionar cuenta para análisis
    print("\n" + "-" * 60)
    customer_id = input("🎯 Ingresa el ID de cuenta a analizar (o presiona Enter para la primera): ").strip()
    
    if not customer_id:
        customer_id = accounts[0]["id"]
        print(f"   → Usando primera cuenta: {customer_id}")
    
    # Remover guiones si los tiene
    customer_id = customer_id.replace("-", "")
    
    print(f"\n🏢 Analizando cuenta: {customer_id}")
    
    # Resultados acumulados
    summary = {}
    
    # Ejecutar cada query de diagnóstico
    for query_name, query_info in DIAGNOSTIC_QUERIES.items():
        print_separator(f"{query_name}: {query_info['description']}")
        
        print(f"\n📋 Query GAQL:")
        print(f"   {query_info['query'][:200]}...")
        
        result = execute_query(
            query_info['query'],
            access_token,
            customer_id,  # USAR variable local, no CUSTOMER_ID global
            LOGIN_CUSTOMER_ID
        )
        
        if result['success']:
            count = result['count']
            print(f"\n✅ Éxito: {count} filas retornadas")
            
            # Contar conversiones totales
            total_conversions = 0
            for row in result['results']:
                metrics = row.get('metrics', {})
                conv = float(metrics.get('conversions', 0) or 0)
                total_conversions += conv
            
            print(f"📈 Total conversiones en resultados: {total_conversions}")
            
            summary[query_name] = {
                "rows": count,
                "conversions": total_conversions,
                "status": "✅"
            }
            
            # Mostrar muestra de datos
            if count > 0:
                print_sample_data(result['results'], max_samples=3)
            
        else:
            print(f"\n❌ Error: {result.get('status', 'N/A')}")
            print(f"   {result.get('error', 'Unknown error')[:300]}")
            summary[query_name] = {
                "rows": 0,
                "conversions": 0,
                "status": "❌",
                "error": result.get('error', '')[:100]
            }
    
    # ============================================================
    # RESUMEN FINAL
    # ============================================================
    print("\n\n" + "=" * 70)
    print("📊 RESUMEN FINAL DEL DIAGNÓSTICO")
    print("=" * 70)
    
    print(f"\n{'Query':<35} {'Filas':<10} {'Conversiones':<15} {'Estado'}")
    print("-" * 70)
    
    for query_name, data in summary.items():
        short_name = query_name[:33]
        print(f"{short_name:<35} {data['rows']:<10} {data['conversions']:<15.2f} {data['status']}")
    
    # Conclusiones
    print("\n\n📋 CONCLUSIONES:")
    print("-" * 70)
    
    # Verificar si hay conversiones en algún nivel
    customer_conv = summary.get("1_CUSTOMER_LEVEL_DAILY", {}).get("conversions", 0)
    campaign_conv = summary.get("2_CAMPAIGN_LEVEL_DAILY", {}).get("conversions", 0)
    hour_conv = summary.get("3_CAMPAIGN_WITH_HOUR", {}).get("conversions", 0)
    
    if customer_conv > 0:
        print(f"✅ La cuenta tiene {customer_conv:.0f} conversiones a nivel CUSTOMER")
        
        if campaign_conv > 0:
            print(f"✅ Las conversiones SÍ se atribuyen a nivel CAMPAIGN ({campaign_conv:.0f})")
        else:
            print("⚠️  Las conversiones NO se atribuyen a nivel CAMPAIGN")
        
        if hour_conv > 0:
            print(f"✅ Las conversiones SÍ tienen segmentación por HORA ({hour_conv:.0f})")
        else:
            print("⚠️  Las conversiones NO tienen segmentación por HORA")
            print("   → Esto es NORMAL en algunas cuentas. La atribución por hora")
            print("   → solo está disponible si Google tiene datos suficientes.")
    else:
        print("⚠️  La cuenta NO tiene conversiones en los últimos 30 días")
        print("   → Verifica que el tracking de conversiones esté configurado")
        print("   → Verifica que las acciones de conversión estén activas")
    
    print("\n" + "🔬" * 35)
    print("   FIN DEL DIAGNÓSTICO")
    print("🔬" * 35 + "\n")


if __name__ == "__main__":
    main()
