#!/bin/bash
# Script para configurar el dominio personalizado para landing pages

echo "🔧 Configuración de Dominio Personalizado para Landing Pages"
echo "=========================================================="

# Configurar variable de entorno
export GITHUB_PAGES_CUSTOM_DOMAIN=consultadebrujosgratis.store

echo "✅ Variable configurada: GITHUB_PAGES_CUSTOM_DOMAIN=$GITHUB_PAGES_CUSTOM_DOMAIN"
echo ""

# Verificar configuración
echo "🎯 Formato de URLs esperado:"
echo "   ✅ Correcto: https://consultadebrujosgratis.store/espiritista-gratis-831/"
echo "   ❌ Incorrecto: espiritista-gratis-831.consultadebrujosgratis.store"
echo ""

echo "⚙️  Para configuración permanente, agrega esta línea a tu ~/.bashrc o ~/.zshrc:"
echo "   export GITHUB_PAGES_CUSTOM_DOMAIN=consultadebrujosgratis.store"
echo ""

echo "📋 Checklist de configuración:"
echo "   1. ✅ Variable de entorno configurada"
echo "   2. 🔧 Configurar dominio en GitHub Pages (ver instrucciones abajo)"
echo "   3. 🔧 Configurar DNS (si es necesario)"
echo ""

echo "🌐 Configuración de GitHub Pages:"
echo "   1. Ve a tu repositorio en GitHub"
echo "   2. Settings → Pages"
echo "   3. Custom domain: consultadebrujosgratis.store"
echo "   4. Save"
echo ""

echo "🔄 Para aplicar cambios, ejecuta:"
echo "   source ~/.bashrc  # o ~/.zshrc"
echo "   # Luego reinicia tu aplicación"