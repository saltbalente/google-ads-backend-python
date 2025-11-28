#!/usr/bin/env python3
"""
Script para iniciar el servidor Flask de manera robusta
"""
import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    print("🌐 URL: http://localhost:8000")
    print("📊 Endpoints disponibles:")
    print("  • GET  /")
    print("  • POST /api/landing/build")
    print("  • GET  /api/landing/history")
    print("  • GET  /api/health")
    print("  • GET  /api/templates")
    print()
    
    app.run(
        host='127.0.0.1',
        port=8000,
        debug=False,
        use_reloader=False,
        threaded=True
    )
