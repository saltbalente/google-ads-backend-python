#!/usr/bin/env python3
"""
Script de prueba para el sistema avanzado de accesibilidad
"""

from web_cloner import AccessibilityAnalyzer

def test_accessibility_analyzer():
    """Prueba el analizador de accesibilidad avanzado"""

    print("=== PRUEBA DEL SISTEMA AVANZADO DE ACCESIBILIDAD ===\n")

    # Inicializar analizador
    analyzer = AccessibilityAnalyzer()

    print(f"📚 Librerías disponibles: {analyzer.libs_available}")

    # Probar análisis básico
    print("\n🔍 Probando análisis básico...")
    basic_report = analyzer._basic_analysis("https://example.com")
    print(f"Score básico: {basic_report.get('overall_score', 'N/A')}")
    print(f"Recomendaciones: {len(basic_report.get('recommendations', []))}")

    # Probar análisis avanzado si está disponible
    if analyzer.libs_available:
        print("\n🚀 Probando análisis avanzado...")
        try:
            # Usar un sitio de prueba pequeño
            test_url = "https://httpbin.org/html"
            print(f"Analizando: {test_url}")

            report = analyzer.analyze_website(test_url)

            print("\n📊 RESULTADOS:")
            print(f"  • Score general: {report.get('overall_score', 'N/A')}/100")
            print(f"  • Problemas de contraste: {len(report.get('contrast_issues', []))}")
            print(f"  • Violaciones totales: {len(report.get('accessibility_violations', []))}")

            severity = report.get('severity_breakdown', {})
            print(f"  • Críticas: {severity.get('critical', 0)}")
            print(f"  • Graves: {severity.get('serious', 0)}")
            print(f"  • Moderadas: {severity.get('moderate', 0)}")
            print(f"  • Menores: {severity.get('minor', 0)}")

            recommendations = report.get('recommendations', [])
            print(f"\n💡 RECOMENDACIONES ({len(recommendations)}):")
            for i, rec in enumerate(recommendations[:5], 1):  # Mostrar máximo 5
                print(f"  {i}. {rec}")

        except Exception as e:
            print(f"❌ Error en análisis avanzado: {e}")
    else:
        print("\n⚠️  Librerías avanzadas no disponibles")
        print("Para análisis completo instalar:")
        print("  pip install axe-selenium-python webcolors colour-science")

    print("\n✅ Prueba completada")

if __name__ == "__main__":
    test_accessibility_analyzer()