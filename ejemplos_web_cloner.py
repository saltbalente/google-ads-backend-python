#!/usr/bin/env python3
"""
Ejemplo de uso del sistema de clonación web
Demuestra diferentes casos de uso del web cloner
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_cloner import WebCloner, WebClonerConfig, clone_website
from github_cloner_uploader import GitHubClonerUploader, upload_cloned_website


def ejemplo_1_clonacion_basica():
    """Ejemplo 1: Clonación básica sin reemplazos"""
    print("\n" + "="*60)
    print("EJEMPLO 1: Clonación Básica")
    print("="*60)
    
    result = clone_website(
        url='https://example.com',
        output_dir='./ejemplos/ejemplo1'
    )
    
    print(f"\n✅ Resultado: {result['success']}")
    print(f"📦 Recursos descargados: {result.get('resources_count', 0)}")
    print(f"📄 Tamaño HTML: {result.get('html_size', 0)} bytes")
    
    return result


def ejemplo_2_con_reemplazos():
    """Ejemplo 2: Clonación con reemplazos de contacto"""
    print("\n" + "="*60)
    print("EJEMPLO 2: Clonación con Reemplazos")
    print("="*60)
    
    result = clone_website(
        url='https://example.com',
        whatsapp='573001234567',
        phone='573001234567',
        gtm_id='GTM-ABC123',
        output_dir='./ejemplos/ejemplo2'
    )
    
    print(f"\n✅ Resultado: {result['success']}")
    print(f"📦 Recursos descargados: {result.get('resources_count', 0)}")
    print(f"📞 WhatsApp reemplazado: 573001234567")
    print(f"📱 Teléfono reemplazado: 573001234567")
    print(f"📊 GTM ID reemplazado: GTM-ABC123")
    
    return result


def ejemplo_3_con_optimizacion():
    """Ejemplo 3: Clonación con optimización de imágenes"""
    print("\n" + "="*60)
    print("EJEMPLO 3: Clonación con Optimización")
    print("="*60)
    
    config = WebClonerConfig()
    config.optimize_images = True
    config.max_image_size = 1024  # Max 1024px por lado
    
    cloner = WebCloner(config)
    result = cloner.clone_website(
        url='https://example.com',
        output_dir='./ejemplos/ejemplo3'
    )
    
    print(f"\n✅ Resultado: {result['success']}")
    print(f"📦 Recursos descargados: {result.get('resources_count', 0)}")
    print(f"🖼️  Imágenes optimizadas a max 1024px")
    
    return result


def ejemplo_4_subida_github():
    """Ejemplo 4: Clonar y subir a GitHub"""
    print("\n" + "="*60)
    print("EJEMPLO 4: Clonar y Subir a GitHub")
    print("="*60)
    
    # Clonar
    cloner = WebCloner()
    result = cloner.clone_website(
        url='https://example.com',
        whatsapp='573001234567',
        gtm_id='GTM-XYZ789'
    )
    
    if not result['success']:
        print("❌ Error al clonar sitio")
        return
    
    print(f"✅ Sitio clonado: {result.get('resources_count', 0)} recursos")
    
    # Subir a GitHub
    print("\n📤 Subiendo a GitHub...")
    
    try:
        uploader = GitHubClonerUploader()
        upload_result = uploader.upload_cloned_website(
            site_name='ejemplo-test',
            resources=cloner.get_resources(),
            optimize_for_jsdelivr=True
        )
        
        if upload_result['success']:
            print(f"\n✅ Subido exitosamente!")
            print(f"🔗 GitHub: {upload_result['github_url']}")
            print(f"🚀 jsDelivr: {upload_result['jsdelivr_url']}")
            print(f"📄 Raw: {upload_result['raw_url']}")
            print(f"📦 Archivos: {upload_result['uploaded_files']}/{upload_result['total_files']}")
        else:
            print(f"❌ Error en subida: {upload_result.get('error', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Verifica que GITHUB_TOKEN esté configurado en .env")


def ejemplo_5_listar_sitios():
    """Ejemplo 5: Listar todos los sitios clonados"""
    print("\n" + "="*60)
    print("EJEMPLO 5: Listar Sitios Clonados")
    print("="*60)
    
    try:
        uploader = GitHubClonerUploader()
        sites = uploader.list_cloned_sites()
        
        if not sites:
            print("\n📭 No hay sitios clonados todavía")
            return
        
        print(f"\n📚 Total de sitios: {len(sites)}\n")
        
        for i, site in enumerate(sites, 1):
            print(f"{i}. {site['name']}")
            print(f"   GitHub: {site['github_url']}")
            print(f"   jsDelivr: {site['jsdelivr_url']}")
            print()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Verifica que GITHUB_TOKEN esté configurado en .env")


def ejemplo_6_configuracion_avanzada():
    """Ejemplo 6: Configuración avanzada personalizada"""
    print("\n" + "="*60)
    print("EJEMPLO 6: Configuración Avanzada")
    print("="*60)
    
    # Crear config personalizada
    config = WebClonerConfig()
    config.timeout = 60  # 60 segundos por recurso
    config.max_file_size = 100 * 1024 * 1024  # 100MB
    config.max_retries = 5  # 5 reintentos
    config.retry_delay = 3  # 3 segundos entre reintentos
    config.optimize_images = True
    config.max_image_size = 2048
    config.user_agent = 'CustomBot/1.0 (WebCloner)'
    
    print("\n⚙️  Configuración:")
    print(f"   Timeout: {config.timeout}s")
    print(f"   Tamaño máximo: {config.max_file_size / 1024 / 1024}MB")
    print(f"   Reintentos: {config.max_retries}")
    print(f"   Optimizar imágenes: {config.optimize_images}")
    print(f"   User-Agent: {config.user_agent}")
    
    cloner = WebCloner(config)
    result = cloner.clone_website(
        url='https://example.com',
        output_dir='./ejemplos/ejemplo6'
    )
    
    print(f"\n✅ Resultado: {result['success']}")
    print(f"📦 Recursos descargados: {result.get('resources_count', 0)}")


def menu_interactivo():
    """Menú interactivo para probar ejemplos"""
    while True:
        print("\n" + "="*60)
        print("🌐 SISTEMA DE CLONACIÓN WEB - EJEMPLOS")
        print("="*60)
        print("\n1. Clonación básica (sin reemplazos)")
        print("2. Clonación con reemplazos (WhatsApp, teléfono, GTM)")
        print("3. Clonación con optimización de imágenes")
        print("4. Clonar y subir a GitHub")
        print("5. Listar sitios clonados en GitHub")
        print("6. Configuración avanzada personalizada")
        print("7. Salir")
        
        opcion = input("\n👉 Selecciona un ejemplo (1-7): ").strip()
        
        if opcion == '1':
            ejemplo_1_clonacion_basica()
        elif opcion == '2':
            ejemplo_2_con_reemplazos()
        elif opcion == '3':
            ejemplo_3_con_optimizacion()
        elif opcion == '4':
            ejemplo_4_subida_github()
        elif opcion == '5':
            ejemplo_5_listar_sitios()
        elif opcion == '6':
            ejemplo_6_configuracion_avanzada()
        elif opcion == '7':
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("\n❌ Opción inválida. Intenta de nuevo.")
        
        input("\n⏎ Presiona Enter para continuar...")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║         🌐 SISTEMA DE CLONACIÓN WEB - EJEMPLOS          ║
║                                                          ║
║  Demuestra las capacidades del web cloner con           ║
║  diferentes casos de uso y configuraciones               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        ejemplo = sys.argv[1]
        
        if ejemplo == '1':
            ejemplo_1_clonacion_basica()
        elif ejemplo == '2':
            ejemplo_2_con_reemplazos()
        elif ejemplo == '3':
            ejemplo_3_con_optimizacion()
        elif ejemplo == '4':
            ejemplo_4_subida_github()
        elif ejemplo == '5':
            ejemplo_5_listar_sitios()
        elif ejemplo == '6':
            ejemplo_6_configuracion_avanzada()
        else:
            print(f"\n❌ Ejemplo '{ejemplo}' no encontrado")
            print("Uso: python ejemplos_web_cloner.py [1-6]")
    else:
        menu_interactivo()
