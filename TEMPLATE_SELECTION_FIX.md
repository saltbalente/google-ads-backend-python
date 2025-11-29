# Corrección del Sistema de Selección de Plantillas

## 📋 Resumen Ejecutivo

Se identificó y corrigió un problema crítico en el sistema de generación de landing pages donde **siempre se utilizaba la plantilla "jose-amp.html"** independientemente de la selección del usuario.

## 🐛 Problema Identificado

### Síntomas
- El usuario seleccionaba una plantilla desde la app iOS (ej: `mystical`, `romantic`, `base`)
- El sistema ignoraba la selección y siempre aplicaba `jose-amp.html`
- Esto ocurría especialmente cuando las palabras clave contenían términos como "amarres", "brujería" o "brujo"

### Causa Raíz

Se identificaron **tres problemas** en el flujo de selección de plantillas:

#### 1. Variable `template_name` no se preservaba
```python
# ANTES (INCORRECTO)
def render(self, gen: GeneratedContent, config: Dict[str, Any]) -> str:
    selected_template = config.get("selected_template")
    
    if selected_template:
        template_name = selected_template if selected_template.endswith('.html') else f"{selected_template}.html"
        # Validación...
        if not available:
            selected_template = None  # ❌ Se perdía template_name aquí
    
    if not selected_template:  # ❌ Siempre entraba aquí por la línea anterior
        # Auto-selección basada en keywords
        template_name = "jose-amp.html"  # Sobrescribía la selección del usuario
```

**Solución**: Inicializar `template_name = None` al inicio y usarla para el control de flujo:

```python
# DESPUÉS (CORRECTO)
def render(self, gen: GeneratedContent, config: Dict[str, Any]) -> str:
    template_name = None  # ✅ Variable de control
    selected_template = config.get("selected_template")
    
    if selected_template:
        template_name = selected_template if selected_template.endswith('.html') else f"{selected_template}.html"
        # Validación...
        if not available:
            template_name = None  # ✅ Reset para auto-selección
    
    if not template_name:  # ✅ Solo auto-selecciona si no hay template válido
        # Auto-selección basada en keywords
```

#### 2. Método estático retornaba nombres sin extensión `.html`

```python
# ANTES (INCORRECTO)
@staticmethod
def get_available_templates() -> List[str]:
    templates = LandingPageGenerator.get_templates_static()
    return [template["name"] for template in templates]  
    # ❌ Retornaba: ["base", "mystical", "romantic"]
```

**Problema**: La validación comparaba `"mystical.html"` (con extensión) contra `"mystical"` (sin extensión), por lo que siempre fallaba.

**Solución**: Asegurar que todos los métodos retornen con extensión:

```python
# DESPUÉS (CORRECTO)
@staticmethod
def get_available_templates() -> List[str]:
    templates = LandingPageGenerator.get_templates_static()
    return [template["name"] + ".html" if not template["name"].endswith(".html") else template["name"] for template in templates]
    # ✅ Retorna: ["base.html", "mystical.html", "romantic.html"]
```

#### 3. Auto-selección se ejecutaba incluso con selección válida

La lógica usaba `if not selected_template:` en lugar de `if not template_name:`, causando que la auto-selección basada en keywords sobrescribiera la selección del usuario.

## ✅ Solución Implementada

### Cambios en `landing_generator.py`

1. **Método `render()` mejorado** (línea 576):
   - Inicialización explícita de `template_name = None`
   - Control de flujo basado en `template_name` en lugar de `selected_template`
   - Logs mejorados para distinguir selección de usuario vs auto-selección

2. **Método `get_available_templates()` corregido** (línea 2287):
   - Retorna todos los nombres con extensión `.html`
   - Consistencia entre método de instancia y estático

### Archivos de Prueba Creados

1. **`test_template_selection.py`**
   - Suite completa de tests automatizados
   - Verifica que la selección del usuario se respete
   - Verifica fallback correcto para templates inválidos
   - Verifica auto-selección cuando no hay selección

2. **`diagnose_templates.py`**
   - Script de diagnóstico para listar templates disponibles
   - Verifica consistencia entre memoria y disco
   - Útil para debugging futuro

## 🧪 Validación

### Tests Ejecutados

```bash
$ python3 test_template_selection.py
```

**Resultados**:
- ✅ **Test 1**: Template mystical seleccionado por usuario (keyword con 'amarres') → **PASÓ**
- ✅ **Test 2**: Template base seleccionado por usuario (keyword con 'brujeria') → **PASÓ**
- ✅ **Test 3**: Template romantic seleccionado por usuario (keyword con 'brujo') → **PASÓ**
- ✅ **Test 4**: Auto-selección sin template especificado (keyword con 'amarres') → **PASÓ**
- ✅ **Test 5**: Validación de templates inexistentes → **PASÓ**

**Resultado final**: **5/5 tests pasaron (100%)**

### Logs de Verificación

```
2025-11-29 01:43:17,937 - INFO - 🎨 Using user-selected template: mystical.html
2025-11-29 01:43:17,943 - INFO - 🎨 Using user-selected template: base.html
2025-11-29 01:43:17,950 - INFO - 🎨 Using user-selected template: romantic.html
2025-11-29 01:43:17,955 - INFO - 🎨 Auto-selected template based on keyword: jose-amp.html
```

## 📊 Comparación Antes/Después

### Escenario: Usuario selecciona "mystical" con keyword "amarres de amor"

#### ANTES (Incorrecto)
```
Input:
  - selected_template: "mystical"
  - primary_keyword: "amarres de amor"

Proceso:
  1. ✓ Usuario selecciona mystical
  2. ✓ Sistema valida que existe
  3. ✗ Variable selected_template se pone en None
  4. ✗ Entra en auto-selección
  5. ✗ Detecta "amarres" en keyword
  6. ✗ Sobrescribe a jose-amp.html

Output:
  - Template usado: jose-amp.html ❌ INCORRECTO
```

#### DESPUÉS (Correcto)
```
Input:
  - selected_template: "mystical"
  - primary_keyword: "amarres de amor"

Proceso:
  1. ✓ Usuario selecciona mystical
  2. ✓ Sistema valida que existe
  3. ✓ template_name = "mystical.html"
  4. ✓ No entra en auto-selección (template_name no es None)
  5. ✓ Usa mystical.html

Output:
  - Template usado: mystical.html ✅ CORRECTO
```

## 🎯 Beneficios

1. **Respeta la elección del usuario**: La plantilla seleccionada en la app iOS se aplica correctamente
2. **No hay conflictos**: Las palabras clave ya no sobrescriben la selección manual
3. **Fallback robusto**: Templates inválidos se manejan correctamente con auto-selección
4. **Mejor debugging**: Logs claros distinguen entre selección manual y automática
5. **Tests automatizados**: Suite de pruebas previene regresiones futuras

## 🚀 Despliegue

```bash
# Commit y push realizados
git commit -m "fix: Corregir selección de plantillas - respetar elección del usuario"
git push origin main
```

**Estado**: ✅ Desplegado en commit `f1b1416`

## 📝 Notas Técnicas

### Templates Disponibles (20 total)

```
1. base.html                        11. brujeria-blanca.html
2. mystical.html                    12. santeria-prosperidad.html
3. romantic.html                    13. curanderismo-ancestral.html
4. prosperity.html                  14. brujeria-negra-venganza.html
5. llama-gemela.html               15. ritual-amor-eterno.html
6. llamado-del-alma.html           16. lectura-aura-sanacion.html
7. el-libro-prohibido.html         17. hechizos-abundancia.html
8. la-luz.html                     18. conexion-guias-espirituales.html
9. amarre-eterno.html              19. nocturnal.html
10. tarot-akashico.html            20. jose-amp.html
```

### Auto-selección (cuando no hay selección del usuario)

La lógica de auto-selección basada en keywords sigue funcionando:
- "tarot" o "cartas" → `mystical.html`
- "brujeria", "brujo" o "amarres" → `jose-amp.html`
- "amor" o "pareja" → `romantic.html`
- "dinero" o "riqueza" → `prosperity.html`
- Por defecto → `base.html`

## 🔍 Verificación en Producción

Para verificar que la corrección funciona en producción:

1. Desde la app iOS, selecciona una plantilla específica (ej: `mystical`)
2. Usa keywords que normalmente activarían otra plantilla (ej: "amarres de amor")
3. Genera la landing page
4. Verifica en los logs del backend:
   ```
   🎨 Using user-selected template: mystical.html
   ```
5. Verifica que el HTML generado use efectivamente el template seleccionado

## 📞 Soporte

Si encuentras algún problema relacionado con la selección de plantillas:

1. Revisa los logs del backend para ver qué template se seleccionó
2. Ejecuta `python3 diagnose_templates.py` para verificar templates disponibles
3. Ejecuta `python3 test_template_selection.py` para validar el sistema

---

**Fecha de corrección**: 29 de noviembre de 2025  
**Autor**: GitHub Copilot  
**Commit**: f1b1416
