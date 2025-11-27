#!/usr/bin/env python3
"""
Script de inicialización para el sistema de automatización.

Ejecutar después de instalar requirements.txt:
    python init_automation_system.py
"""

import os
import sys

def check_dependencies():
    """Verifica que todas las dependencias estén instaladas"""
    print("🔍 Verificando dependencias...")
    
    required = [
        'flask',
        'sqlalchemy',
        'google.ads.googleads',
        'openai',
        'google.generativeai'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Faltan dependencias: {', '.join(missing)}")
        print("💡 Ejecuta: pip install -r requirements.txt")
        return False
    
    print("✅ Todas las dependencias instaladas")
    return True


def check_environment_variables():
    """Verifica variables de entorno necesarias"""
    print("\n🔍 Verificando variables de entorno...")
    
    required = [
        'GOOGLE_ADS_DEVELOPER_TOKEN',
        'GOOGLE_ADS_CLIENT_ID',
        'GOOGLE_ADS_CLIENT_SECRET',
        'GOOGLE_ADS_REFRESH_TOKEN',
        'GOOGLE_ADS_LOGIN_CUSTOMER_ID'
    ]
    
    optional = [
        'OPENAI_API_KEY',
        'GOOGLE_API_KEY',
        'DEEPSEEK_API_KEY'
    ]
    
    # Verificar requeridas
    missing = []
    for var in required:
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Faltan variables de entorno requeridas:")
        for var in missing:
            print(f"   - {var}")
        print("\n💡 Agrégalas al archivo .env o al sistema")
        return False
    
    print("✅ Variables de Google Ads configuradas")
    
    # Verificar opcionales (IA)
    ai_configured = False
    for var in optional:
        if os.environ.get(var):
            ai_configured = True
            print(f"✅ {var} configurada")
    
    if not ai_configured:
        print("⚠️  Ningún proveedor de IA configurado")
        print("   Configura al menos una de estas variables:")
        for var in optional:
            print(f"   - {var}")
    
    return True


def initialize_database():
    """Inicializa la base de datos"""
    print("\n🔍 Inicializando base de datos...")
    
    try:
        from automation_models import init_db
        init_db()
        print("✅ Base de datos inicializada correctamente")
        print("   📁 Archivo: automation_jobs.db")
        return True
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {str(e)}")
        return False


def test_worker():
    """Prueba el worker"""
    print("\n🔍 Probando worker de automatización...")
    
    try:
        from automation_worker import get_worker
        worker = get_worker(max_workers=3)
        print("✅ Worker inicializado correctamente")
        print(f"   👷 Capacidad: 3 workers concurrentes")
        return True
    except Exception as e:
        print(f"❌ Error inicializando worker: {str(e)}")
        return False


def print_summary():
    """Imprime resumen de configuración"""
    print("\n" + "="*60)
    print("🎉 SISTEMA DE AUTOMATIZACIÓN INICIALIZADO")
    print("="*60)
    
    print("\n📋 ENDPOINTS DISPONIBLES:")
    print("   POST   /api/automation/start")
    print("   GET    /api/automation/status/<job_id>")
    print("   POST   /api/automation/history")
    print("   POST   /api/automation/cancel/<job_id>")
    print("   GET    /api/automation/logs/<job_id>")
    
    print("\n🚀 PARA INICIAR EL SERVIDOR:")
    print("   python app.py")
    print("   # o en producción:")
    print("   gunicorn app:app --workers 4 --bind 0.0.0.0:5000")
    
    print("\n📖 DOCUMENTACIÓN:")
    print("   Ver: AUTOMATION_SYSTEM_GUIDE.md")
    
    print("\n✅ ¡Sistema listo para usar!")
    print("="*60 + "\n")


def main():
    """Función principal"""
    print("="*60)
    print("🔧 INICIALIZANDO SISTEMA DE AUTOMATIZACIÓN")
    print("="*60 + "\n")
    
    # Verificar dependencias
    if not check_dependencies():
        sys.exit(1)
    
    # Verificar variables de entorno
    if not check_environment_variables():
        sys.exit(1)
    
    # Inicializar base de datos
    if not initialize_database():
        sys.exit(1)
    
    # Probar worker
    if not test_worker():
        sys.exit(1)
    
    # Imprimir resumen
    print_summary()


if __name__ == '__main__':
    main()
