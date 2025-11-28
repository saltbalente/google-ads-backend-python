#!/usr/bin/env python3
"""
Script para configurar dominio personalizado en GitHub Pages
"""
import os
import sys
import requests
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

def setup_custom_domain():
    """Configura dominio personalizado para GitHub Pages"""

    # Variables requeridas
    owner = os.getenv("GITHUB_REPO_OWNER")
    repo = os.getenv("GITHUB_REPO_NAME", "monorepo-landings")
    token = os.getenv("GITHUB_TOKEN")
    custom_domain = os.getenv("GITHUB_PAGES_CUSTOM_DOMAIN")

    if not all([owner, token, custom_domain]):
        print("❌ Faltan variables de entorno:")
        print("   GITHUB_REPO_OWNER: requerido")
        print("   GITHUB_TOKEN: requerido")
        print("   GITHUB_PAGES_CUSTOM_DOMAIN: requerido")
        print("\nEjemplo:")
        print("   GITHUB_PAGES_CUSTOM_DOMAIN=landing-pages.miexperto.com")
        return False

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    print(f"🔧 Configurando dominio personalizado: {custom_domain}")
    print(f"📂 Repositorio: {owner}/{repo}")

    try:
        # 1. Crear/verificar archivo CNAME
        print("\n📄 Paso 1: Configurando archivo CNAME...")

        # Verificar si CNAME existe
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/CNAME",
            headers=headers
        )

        sha = None
        if response.status_code == 200:
            data = response.json()
            sha = data.get("sha")
            print("   📝 CNAME existe, actualizando...")
        elif response.status_code == 404:
            print("   📝 CNAME no existe, creando...")
        else:
            print(f"   ❌ Error verificando CNAME: {response.status_code}")
            return False

        # Crear/actualizar CNAME
        cname_payload = {
            "message": f"🚀 Configure custom domain: {custom_domain}",
            "content": base64.b64encode(custom_domain.encode()).decode(),
            "branch": "main"
        }

        if sha:
            cname_payload["sha"] = sha

        response = requests.put(
            f"https://api.github.com/repos/{owner}/{repo}/contents/CNAME",
            headers=headers,
            json=cname_payload
        )

        if response.status_code not in [200, 201]:
            print(f"   ❌ Error creando CNAME: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False

        print("   ✅ CNAME configurado correctamente")

        # 2. Verificar configuración de GitHub Pages
        print("\n📄 Paso 2: Verificando GitHub Pages...")

        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pages",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            current_domain = data.get("cname")
            if current_domain == custom_domain:
                print(f"   ✅ GitHub Pages ya configurado con dominio: {current_domain}")
            else:
                print(f"   ⚠️  GitHub Pages configurado con dominio diferente: {current_domain}")
                print(f"      Actualizando a: {custom_domain}")
        elif response.status_code == 404:
            print("   📄 GitHub Pages no configurado, configurando...")
        else:
            print(f"   ❌ Error verificando Pages: {response.status_code}")
            return False

        # 3. Configurar dominio en GitHub Pages (si es necesario)
        if response.status_code == 404 or (response.status_code == 200 and data.get("cname") != custom_domain):
            print(f"\n🔧 Configurando dominio en GitHub Pages...")

            pages_config = {
                "cname": custom_domain,
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }

            response = requests.post(
                f"https://api.github.com/repos/{owner}/{repo}/pages",
                headers=headers,
                json=pages_config
            )

            if response.status_code in [201, 204]:
                print("   ✅ Dominio configurado en GitHub Pages")
            else:
                print(f"   ❌ Error configurando dominio: {response.status_code}")
                print(f"   Respuesta: {response.text}")
                return False

        print("
🎉 ¡Dominio personalizado configurado exitosamente!"        print(f"🌐 Dominio: {custom_domain}")
        print(f"📂 Repositorio: https://github.com/{owner}/{repo}")
        print("
⚠️  IMPORTANTE: Configura tu DNS"        print("   1. Ve a tu proveedor de dominio"        print(f"   2. Crea registro CNAME: *.{custom_domain} -> {owner}.github.io")
        print("   3. O alternativamente: CNAME www -> " + owner + ".github.io")
        print("   4. Espera 24-48 horas para propagación DNS")

        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_subdomain_generation():
    """Prueba cómo se generarían los subdominios"""

    custom_domain = os.getenv("GITHUB_PAGES_CUSTOM_DOMAIN", "landing-pages.miexperto.com")

    print("
🧪 PRUEBA DE GENERACIÓN DE SUBDOMINIOS"    print(f"Dominio base: {custom_domain}")
    print("-" * 50)

    test_keywords = [
        "landing-tarot-gratis",
        "landing-lectura-tarot",
        "landing-tarot-online",
        "landing-amor-verdadero"
    ]

    for keyword in test_keywords:
        # Simular build_alias_domain
        alias = keyword.lower().replace("landing-", "")
        subdomain = f"{alias}.{custom_domain}"
        print(f"📄 {keyword} -> https://{subdomain}/")

    print("
✅ Los subdominios se generan automáticamente!"    print("   Cada landing page tendrá su propio subdominio único."

if __name__ == "__main__":
    import base64

    print("🚀 CONFIGURACIÓN DE DOMINIO PERSONALIZADO PARA GITHUB PAGES")
    print("=" * 70)

    # Mostrar configuración actual
    print("📋 CONFIGURACIÓN ACTUAL:")
    print(f"   GITHUB_REPO_OWNER: {os.getenv('GITHUB_REPO_OWNER', 'NO CONFIGURADO')}")
    print(f"   GITHUB_REPO_NAME: {os.getenv('GITHUB_REPO_NAME', 'monorepo-landings')}")
    print(f"   GITHUB_TOKEN: {'CONFIGURADO' if os.getenv('GITHUB_TOKEN') else 'NO CONFIGURADO'}")
    print(f"   GITHUB_PAGES_CUSTOM_DOMAIN: {os.getenv('GITHUB_PAGES_CUSTOM_DOMAIN', 'NO CONFIGURADO')}")

    print("
🔧 PASOS PARA CONFIGURAR:"    print("   1. Compra un dominio (ej: landing-pages.com)"    print("   2. Configura variable: GITHUB_PAGES_CUSTOM_DOMAIN=tudominio.com"    print("   3. Ejecuta este script"    print("   4. Configura DNS en tu proveedor de dominio"    print("   5. ¡Listo! Las landing pages usarán subdominios"

    # Ejecutar configuración
    if os.getenv("GITHUB_PAGES_CUSTOM_DOMAIN"):
        print("
⚙️  EJECUTANDO CONFIGURACIÓN..."        success = setup_custom_domain()
        if success:
            test_subdomain_generation()
    else:
        print("
❌ No hay dominio personalizado configurado."        print("   Configura GITHUB_PAGES_CUSTOM_DOMAIN para continuar."
        test_subdomain_generation()