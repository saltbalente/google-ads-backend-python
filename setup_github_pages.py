#!/usr/bin/env python3
"""
Script para configurar GitHub Pages automáticamente en el repositorio
"""
import os
import sys
import requests
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

def setup_github_pages_auto():
    """Configura GitHub Pages automáticamente"""

    # Variables requeridas
    owner = os.getenv("GITHUB_REPO_OWNER")
    repo = os.getenv("GITHUB_REPO_NAME", "monorepo-landings")
    token = os.getenv("GITHUB_TOKEN")

    if not all([owner, token]):
        print("❌ Faltan variables de entorno: GITHUB_REPO_OWNER, GITHUB_TOKEN")
        return False

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    print(f"🔧 Configurando GitHub Pages para {owner}/{repo}...")

    try:
        # Verificar si Pages ya está configurado
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/pages",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("source", {}).get("branch") == "main":
                print("✅ GitHub Pages ya está configurado")
                return True

        # Configurar GitHub Pages
        config = {
            "source": {
                "branch": "main",
                "path": "/"
            }
        }

        response = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/pages",
            headers=headers,
            json=config
        )

        if response.status_code in [201, 204]:
            print("✅ GitHub Pages configurado exitosamente")
            print(f"🌐 URL: https://{owner}.github.io/{repo}/")
            return True
        else:
            print(f"❌ Error configurando GitHub Pages: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = setup_github_pages_auto()
    if success:
        print("\n🎉 ¡GitHub Pages está listo para hosting automático!")
        print("Ahora puedes generar landing pages sin configuración adicional.")
    else:
        print("\n❌ No se pudo configurar GitHub Pages automáticamente.")
        print("Revisa los permisos del token y las variables de entorno.")</content>
<parameter name="filePath">/Users/edwarbechara/Documents/app-reportes-pagos-BACKUP-20250702-123421/google-ads-backend-python/setup_github_pages.py