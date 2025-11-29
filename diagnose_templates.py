#!/usr/bin/env python3
"""
Script de diagnóstico para verificar qué templates están disponibles.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from landing_generator import LandingPageGenerator


def main():
    print("🔍 Diagnóstico de Templates Disponibles")
    print("=" * 80)
    
    try:
        gen = LandingPageGenerator()
        
        # Obtener templates disponibles
        templates = gen.get_available_templates()
        
        print(f"\n📁 Directorio de templates: {gen.templates_dir}")
        print(f"📝 Total de templates encontrados: {len(templates)}")
        print("\nListado completo (con extensión):")
        print("-" * 80)
        
        for i, template in enumerate(templates, 1):
            print(f"  {i}. {template}")
        
        # Verificar templates específicos
        print("\n🔍 Verificación de templates clave:")
        print("-" * 80)
        
        key_templates = ['base.html', 'mystical.html', 'romantic.html', 'jose-amp.html', 
                        'prosperity.html', 'nocturnal.html']
        
        for template in key_templates:
            if template in templates:
                print(f"  ✅ {template} - DISPONIBLE")
            else:
                print(f"  ❌ {template} - NO ENCONTRADO")
        
        # Verificar físicamente los archivos
        print("\n🗂️  Verificación física de archivos:")
        print("-" * 80)
        
        templates_path = gen.templates_dir
        if os.path.exists(templates_path):
            files = [f for f in os.listdir(templates_path) if f.endswith('.html')]
            print(f"  Total archivos .html en disco: {len(files)}")
            
            # Comparar listas
            if set(templates) == set(files):
                print("  ✅ La lista en memoria coincide con el disco")
            else:
                print("  ⚠️  Discrepancia encontrada:")
                in_memory_only = set(templates) - set(files)
                in_disk_only = set(files) - set(templates)
                
                if in_memory_only:
                    print(f"     Solo en memoria: {in_memory_only}")
                if in_disk_only:
                    print(f"     Solo en disco: {in_disk_only}")
        else:
            print(f"  ❌ Directorio no existe: {templates_path}")
        
        print("\n✅ Diagnóstico completado")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error durante el diagnóstico: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
