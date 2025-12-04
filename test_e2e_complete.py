#!/usr/bin/env python3
"""
Test completo E2E local: simula el flujo completo del backend
"""
import sys
sys.path.insert(0, '.')

from github_cloner_uploader import GitHubClonerUploader
import time

print("=" * 70)
print("🧪 TEST E2E: Simulando flujo completo del backend")
print("=" * 70)

# Simular recursos descargados (como los que vienen de Playwright o requests)
print("\n1️⃣ Simulando descarga de sitio web...")

resources = {
    'index.html': {
        'content': '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Test Site - Dual System</title>
    <link rel="stylesheet" href="main.css">
    <link rel="stylesheet" href="styles/theme.css">
    <script src="app.js"></script>
    <script src="js/analytics.js"></script>
</head>
<body>
    <header>
        <img src="logo.png" alt="Logo" class="logo">
        <img src="images/banner.jpg" alt="Banner">
    </header>
    <main style="background: url(bg.jpg)">
        <div class="hero" style="background-image: url('images/hero.jpg')">
            <h1>Welcome</h1>
        </div>
    </main>
    <footer>
        <script src="footer.js"></script>
    </footer>
</body>
</html>''',
        'type': 'text/html',
        'url': 'https://example.com/index.html'
    },
    'main.css': {
        'content': '''/* Main styles */
body {
    background: url(bg.jpg);
    font-family: Arial, sans-serif;
}

.header {
    background-image: url('images/header-bg.jpg');
}

.logo {
    content: url(logo.png);
}

@import url('styles/theme.css');

.hero {
    background: url("images/hero.jpg") no-repeat;
}''',
        'type': 'text/css',
        'url': 'https://example.com/main.css'
    },
    'app.js': {
        'content': 'console.log("App loaded");',
        'type': 'application/javascript',
        'url': 'https://example.com/app.js'
    },
    'logo.png': {
        'content': b'\x89PNG fake image data',
        'type': 'image/png',
        'url': 'https://example.com/logo.png'
    },
    'bg.jpg': {
        'content': b'\xff\xd8\xff fake jpg data',
        'type': 'image/jpeg',
        'url': 'https://example.com/bg.jpg'
    }
}

print(f"✅ {len(resources)} archivos simulados")

# Paso 2: Subir a GitHub (como hace el backend)
print("\n2️⃣ Subiendo a GitHub...")

uploader = GitHubClonerUploader()
site_name = f'test-e2e-full-{int(time.time())}'

upload_result = uploader.upload_cloned_website(
    site_name=site_name,
    resources=resources,
    optimize_for_jsdelivr=True
)

if not upload_result.get('success'):
    print(f"❌ Error: {upload_result.get('error')}")
    sys.exit(1)

print(f"✅ Subida exitosa!")
print(f"   📊 Archivos subidos: {upload_result['uploaded_files']}")
print(f"   ❌ Archivos fallidos: {upload_result['failed_files']}")

# Mostrar URLs
print(f"\n3️⃣ URLs generadas:")
print(f"   🔗 GitHub: {upload_result['github_url']}")
print(f"   🔗 jsDelivr: {upload_result['jsdelivr_url']}")

# Esperar a que GitHub procese
print(f"\n4️⃣ Esperando 15 segundos para que GitHub procese...")
time.sleep(15)

# Verificar archivos en GitHub
print(f"\n5️⃣ Verificando archivos en GitHub...")

import requests

base_url = f"https://raw.githubusercontent.com/saltbalente/cloned-websites/main/clonedwebs/{site_name}"

files_to_check = ['index.html', 'index-vercel.html', 'main.css', 'app.js', 'logo.png', 'bg.jpg']

for filename in files_to_check:
    url = f"{base_url}/{filename}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            size = len(response.content)
            
            if filename in ['index.html', 'index-vercel.html', 'main.css']:
                has_cdn = b'cdn.jsdelivr.net' in response.content
                print(f"   ✅ {filename}: {size} bytes, jsDelivr: {has_cdn}")
                
                if filename == 'index.html' and not has_cdn:
                    print(f"      ⚠️  PROBLEMA: index.html debería tener URLs de jsDelivr!")
                elif filename == 'index-vercel.html' and has_cdn:
                    print(f"      ⚠️  PROBLEMA: index-vercel.html NO debería tener URLs de jsDelivr!")
            else:
                print(f"   ✅ {filename}: {size} bytes")
        else:
            print(f"   ❌ {filename}: Error {response.status_code}")
    except Exception as e:
        print(f"   ❌ {filename}: {str(e)}")

# Esperar más para jsDelivr CDN
print(f"\n6️⃣ Esperando 20 segundos para que jsDelivr CDN actualice...")
time.sleep(20)

# Verificar en jsDelivr
print(f"\n7️⃣ Verificando en jsDelivr CDN...")

cdn_base = f"https://cdn.jsdelivr.net/gh/saltbalente/cloned-websites@main/clonedwebs/{site_name}"

for filename in ['index.html', 'index-vercel.html', 'main.css']:
    url = f"{cdn_base}/{filename}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            size = len(response.content)
            has_cdn = b'cdn.jsdelivr.net' in response.content
            print(f"   ✅ {filename}: {size} bytes, jsDelivr URLs: {has_cdn}")
        else:
            print(f"   ❌ {filename}: Error {response.status_code}")
    except Exception as e:
        print(f"   ❌ {filename}: {str(e)}")

print("\n" + "=" * 70)
print("✅ TEST E2E COMPLETADO")
print("=" * 70)
print(f"\n📦 Para verificar manualmente:")
print(f"   GitHub: https://github.com/saltbalente/cloned-websites/tree/main/clonedwebs/{site_name}")
print(f"   Preview: {cdn_base}/index.html")
print(f"   Deployment: {cdn_base}/index-vercel.html")
