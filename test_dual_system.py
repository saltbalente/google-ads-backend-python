#!/usr/bin/env python3
"""
Test script para verificar el sistema dual de preview y deployment
"""

import sys
import os
sys.path.insert(0, '.')

from github_cloner_uploader import GitHubClonerUploader

# Crear recursos de prueba simulados
print('🚀 Creando recursos de prueba simulados...')

resources = {
    'index.html': {
        'content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Test Site</title>
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="fonts/custom.css">
    <script src="script.js"></script>
</head>
<body>
    <img src="logo.png" alt="Logo">
    <img src="images/banner.jpg">
    <div style="background: url(bg.jpg)">Content</div>
</body>
</html>''',
        'type': 'text/html',
        'url': 'https://example.com/index.html'
    },
    'style.css': {
        'content': '''body {
    background: url(bg.jpg);
    font-family: Arial;
}
.logo {
    background-image: url('logo.png');
}
@import url('fonts/custom.css');''',
        'type': 'text/css',
        'url': 'https://example.com/style.css'
    },
    'script.js': {
        'content': 'console.log("test");',
        'type': 'application/javascript',
        'url': 'https://example.com/script.js'
    },
    'logo.png': {
        'content': b'PNG_DATA',
        'type': 'image/png',
        'url': 'https://example.com/logo.png'
    },
    'bg.jpg': {
        'content': b'JPG_DATA',
        'type': 'image/jpeg',
        'url': 'https://example.com/bg.jpg'
    }
}

print(f'✅ {len(resources)} archivos de prueba creados')

# Simular el proceso de optimización
print('\n🚀 Paso 1: Creando versiones (preview + deployment)...')
uploader = GitHubClonerUploader()
folder_path = 'clonedwebs/test-local'

# Guardar original
original_index = resources['index.html'].copy()
original_css = resources['style.css'].copy()

# Crear versión optimizada (como lo hace upload_cloned_website)
files_to_upload = {}

# Optimizar para jsDelivr
preview_resources = uploader._optimize_for_jsdelivr(resources.copy(), folder_path)

# Agregar todos los archivos optimizados
files_to_upload.update(preview_resources)

# Agregar versión original como index-vercel.html
files_to_upload['index-vercel.html'] = original_index

print(f'✅ Archivos preparados para subir: {len(files_to_upload)}')
print(f'   Archivos: {list(files_to_upload.keys())}')

# Analizar index.html (preview)
print('\n' + '='*80)
print('📊 ANÁLISIS: index.html (preview con jsDelivr)')
print('='*80)
preview_html = files_to_upload['index.html']['content']
if isinstance(preview_html, bytes):
    preview_html = preview_html.decode('utf-8')

print(f'✅ Contiene cdn.jsdelivr.net: {("cdn.jsdelivr.net" in preview_html)}')
print(f'✅ Ocurrencias de jsDelivr: {preview_html.count("cdn.jsdelivr.net")}')
print('\nContenido:')
print(preview_html)

# Analizar style.css (preview)
print('\n' + '='*80)
print('📊 ANÁLISIS: style.css (preview con jsDelivr)')
print('='*80)
preview_css = files_to_upload['style.css']['content']
if isinstance(preview_css, bytes):
    preview_css = preview_css.decode('utf-8')

print(f'✅ Contiene cdn.jsdelivr.net: {("cdn.jsdelivr.net" in preview_css)}')
print(f'✅ Ocurrencias de jsDelivr: {preview_css.count("cdn.jsdelivr.net")}')
print('\nContenido:')
print(preview_css)

# Analizar index-vercel.html (deployment)
print('\n' + '='*80)
print('📊 ANÁLISIS: index-vercel.html (deployment - rutas originales)')
print('='*80)
deployment_html = files_to_upload['index-vercel.html']['content']
if isinstance(deployment_html, bytes):
    deployment_html = deployment_html.decode('utf-8')

print(f'✅ NO contiene cdn.jsdelivr.net: {("cdn.jsdelivr.net" not in deployment_html)}')
print(f'✅ Mantiene rutas originales: {("style.css" in deployment_html and "logo.png" in deployment_html)}')
print('\nContenido:')
print(deployment_html)

# Guardar archivos
test_dir = '/tmp/test-cloner-dual'
os.makedirs(test_dir, exist_ok=True)

print('\n' + '='*80)
print(f'💾 Guardando archivos en {test_dir}...')
print('='*80)

for filename, data in files_to_upload.items():
    content = data['content']
    mode = 'wb' if isinstance(content, bytes) else 'w'
    encoding = None if isinstance(content, bytes) else 'utf-8'
    
    filepath = os.path.join(test_dir, filename)
    with open(filepath, mode, encoding=encoding) as f:
        f.write(content)
    print(f'  ✅ {filename}')

# Resumen final
print('\n' + '='*80)
print('🎉 PRUEBA LOCAL COMPLETADA')
print('='*80)

cdn_count_html = preview_html.count("cdn.jsdelivr.net")
cdn_count_css = preview_css.count("cdn.jsdelivr.net")

print('\n✅ Verificaciones:')
print(f'  1. index.html tiene {cdn_count_html} URLs de jsDelivr: {"✅" if cdn_count_html > 0 else "❌"}')
print(f'  2. style.css tiene {cdn_count_css} URLs de jsDelivr: {"✅" if cdn_count_css > 0 else "❌"}')
print(f'  3. index-vercel.html sin jsDelivr: {"✅" if "cdn.jsdelivr.net" not in deployment_html else "❌"}')
print(f'  4. index-vercel.html con rutas originales: {"✅" if "style.css" in deployment_html else "❌"}')
print(f'  5. Total de archivos: {len(files_to_upload)} {"✅" if len(files_to_upload) == 6 else "❌"}')

all_good = (
    cdn_count_html > 0 and 
    cdn_count_css > 0 and 
    "cdn.jsdelivr.net" not in deployment_html and
    "style.css" in deployment_html and
    len(files_to_upload) == 6
)

if all_good:
    print('\n🎉 ¡SISTEMA DUAL FUNCIONANDO CORRECTAMENTE!')
else:
    print('\n⚠️  Hay problemas con el sistema dual')

print(f'\n📂 Archivos guardados en: {test_dir}')
print(f'\n🔍 Puedes verificar con:')
print(f'  cat {test_dir}/index.html')
print(f'  cat {test_dir}/index-vercel.html')
print(f'  cat {test_dir}/style.css')
