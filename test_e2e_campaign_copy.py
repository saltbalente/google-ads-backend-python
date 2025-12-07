#!/usr/bin/env python3
"""
Test end-to-end completo del flujo de copia de campaña
Simula exactamente lo que hace Swift
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = "http://localhost:5000"  # Cambiar a http://localhost:5000 para test local
CUSTOMER_ID = "6639082872"

def get_access_token():
    """En producción, esto vendría del OAuth2 de iOS"""
    # Para testing, retornamos un token dummy ya que usaremos las credenciales del backend
    return "dummy_token"

def test_full_campaign_copy_flow():
    """Prueba el flujo completo de copia de campaña"""
    
    print("🧪 ===================================")
    print("🧪 TEST END-TO-END: Campaign Copy Flow")
    print("🧪 ===================================\n")
    
    # Sin headers OAuth - el backend usará las credenciales por defecto del .env
    headers = {
        "Content-Type": "application/json"
    }
    
    # Paso 1: Crear presupuesto NO compartido
    print("📋 Paso 1: Creando presupuesto (isShared=False)...")
    budget_payload = {
        "customerId": CUSTOMER_ID,
        "name": f"TEST Budget E2E {int(os.popen('date +%s').read())}",
        "amountMicros": "470000000000",  # $470,000 COP
        "isShared": False  # ¡CRÍTICO!
    }
    
    response = requests.post(
        f"{BACKEND_URL}/api/create-budget",
        json=budget_payload,
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    if response.status_code != 200:
        print("❌ FAILED: Budget creation failed")
        return False
    
    budget_data = response.json()
    if not budget_data.get('success'):
        print(f"❌ FAILED: {budget_data.get('error')}")
        return False
    
    budget_resource_name = budget_data['resourceName']
    print(f"✅ Budget creado: {budget_resource_name}\n")
    
    # Paso 2: Crear campaña con MAXIMIZE_CONVERSIONS
    print("📋 Paso 2: Creando campaña (MAXIMIZE_CONVERSIONS)...")
    campaign_payload = {
        "customerId": CUSTOMER_ID,
        "name": f"TEST Campaign E2E {int(os.popen('date +%s').read())}",
        "budgetResourceName": budget_resource_name,
        "status": "PAUSED",  # PAUSED para prueba
        "biddingStrategy": "MAXIMIZE_CONVERSIONS",
        "networkSettings": {
            "targetGoogleSearch": True,
            "targetSearchNetwork": True,
            "targetContentNetwork": False,
            "targetPartnerSearchNetwork": False
        }
    }
    
    response = requests.post(
        f"{BACKEND_URL}/api/create-campaign",
        json=campaign_payload,
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    if response.status_code != 200:
        print("❌ FAILED: Campaign creation failed")
        return False
    
    campaign_data = response.json()
    if not campaign_data.get('success'):
        print(f"❌ FAILED: {campaign_data.get('error')}")
        return False
    
    campaign_id = campaign_data['campaignId']
    print(f"✅ Campaign creada: {campaign_id}\n")
    
    print("🎉 ===================================")
    print("🎉 TEST PASSED: Todo el flujo funciona correctamente")
    print("🎉 ===================================")
    
    return True

if __name__ == "__main__":
    # Nota: Este test requiere que el backend esté corriendo
    print("⚠️  NOTA: Asegúrate de que el backend esté corriendo en localhost:5000")
    print("⚠️  Ejecuta: python3 app.py\n")
    
    import time
    time.sleep(2)
    
    try:
        success = test_full_campaign_copy_flow()
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se puede conectar al backend")
        print("   Ejecuta: python3 app.py")
        exit(1)
