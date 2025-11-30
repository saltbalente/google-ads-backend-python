#!/bin/bash
# Script de inicio rápido para el sistema de clonación web

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║      🌐 SISTEMA DE CLONACIÓN WEB - INICIO RÁPIDO        ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Instala Python 3.9+"
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activate virtual environment
echo ""
echo "🔄 Activando entorno virtual..."
source venv/bin/activate

# Install dependencies
echo ""
echo "📥 Instalando dependencias..."
pip install -q --upgrade pip
pip install -q requests beautifulsoup4 pillow python-dotenv flask

# Check .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  Archivo .env no encontrado"
    echo ""
    echo "Creando .env con valores por defecto..."
    
    cat > .env << 'EOF'
# GitHub Configuration
GITHUB_TOKEN=tu_token_aqui
GITHUB_REPO_OWNER=tu_usuario
GITHUB_CLONED_REPO=cloned-websites

# Backend URL (para iOS app)
BACKEND_URL=http://localhost:5000
EOF
    
    echo "✅ Archivo .env creado"
    echo ""
    echo "⚙️  IMPORTANTE: Edita .env y configura:"
    echo "   - GITHUB_TOKEN (obtén uno en https://github.com/settings/tokens)"
    echo "   - GITHUB_REPO_OWNER (tu usuario de GitHub)"
    echo ""
    read -p "⏎ Presiona Enter cuando hayas configurado .env..."
fi

# Run tests
echo ""
echo "🧪 Ejecutando tests..."
echo ""
python test_web_cloner.py

if [ $? -eq 0 ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║                                                          ║"
    echo "║  ✅ SISTEMA LISTO PARA USAR                              ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "📚 Opciones disponibles:"
    echo ""
    echo "1️⃣  Clonar desde línea de comandos:"
    echo "   python web_cloner.py https://example.com"
    echo ""
    echo "2️⃣  Ejecutar ejemplos interactivos:"
    echo "   python ejemplos_web_cloner.py"
    echo ""
    echo "3️⃣  Iniciar servidor API:"
    echo "   python app.py"
    echo ""
    echo "4️⃣  Listar sitios clonados:"
    echo "   python github_cloner_uploader.py list"
    echo ""
    echo "5️⃣  Usar desde la app iOS:"
    echo "   Dashboard → Herramientas SEO → Web Cloner"
    echo ""
    echo "📖 Lee WEB_CLONER_README.md para más información"
    echo ""
else
    echo ""
    echo "❌ Algunos tests fallaron. Revisa la configuración."
    echo ""
    echo "💡 Problemas comunes:"
    echo "   - Verifica GITHUB_TOKEN en .env"
    echo "   - Asegúrate de tener conexión a internet"
    echo "   - Revisa que las dependencias estén instaladas"
    echo ""
fi
