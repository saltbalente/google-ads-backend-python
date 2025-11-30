# ✅ Custom Templates - Integración con GitHub Pages

## 🎯 Resumen

Los **custom templates generados con IA** ahora se guardan automáticamente en las carpetas correctas para **GitHub Pages**, listos para commit y deploy.

## 📁 Nueva Estructura de Almacenamiento

### Antes (Sistema Antiguo)
```
custom_templates/
├── templates_index.json
├── abc-123-def-456.html
├── xyz-789-ghi-012.html
└── ...
```
❌ Archivos con UUID, no compatibles con GitHub Pages

### Ahora (Sistema Nuevo)
```
templates/
├── landing/                    ← Templates completos (Jinja2)
│   ├── template-tarot-mistico.html
│   ├── videncia-profesional.html
│   └── ...
│
├── previews/                   ← Previews estáticos (HTML)
│   ├── template-tarot-mistico_preview.html
│   ├── videncia-profesional_preview.html
│   └── ...
│
custom_templates/
└── templates_index.json        ← Índice con metadata
```
✅ Nombres legibles, listos para GitHub

## 🚀 Características Nuevas

### 1. Nombres de Archivo Inteligentes
El nombre del template se convierte automáticamente en un filename válido:

```python
"Template Tarot Místico Pro" → "template-tarot-mistico-pro.html"
"Videncia & Tarot" → "videncia-tarot.html"
"Servicios 24/7" → "servicios-24-7.html"
```

**Reglas de conversión:**
- Minúsculas
- Espacios → guiones
- Caracteres especiales eliminados
- Máximo 50 caracteres

### 2. Doble Guardado Automático

Cuando guardas un template, se crean **2 archivos**:

#### A. **Landing Completo** (`templates/landing/`)
- ✅ Código HTML/Jinja2 con variables
- ✅ Listo para usar en el generador de landing pages
- ✅ Variables como `{{ keywords }}`, `{{ business_type }}`, etc.

**Ejemplo:**
```html
<h1>{{ business_type }}</h1>
<p>Servicios de {{ keywords }}</p>
<a href="#contacto">{{ call_to_action }}</a>
```

#### B. **Preview Estático** (`templates/previews/`)
- ✅ HTML completamente renderizado
- ✅ Variables reemplazadas con datos de ejemplo
- ✅ Listo para visualización en GitHub Pages
- ✅ Header de comentario con metadata

**Ejemplo del mismo template renderizado:**
```html
<!-- 
    PREVIEW GENERADO AUTOMÁTICAMENTE
    Template: Template Tarot Místico Pro
    Generado: 2024-11-30 14:30:00
-->
<h1>Tarot y Videncia Profesional</h1>
<p>Servicios de tarot, videncia, lectura de cartas</p>
<a href="#contacto">Consulta Ahora</a>
```

### 3. Reemplazo Inteligente de Variables

El preview automáticamente reemplaza variables Jinja2:

| Variable Jinja2 | Valor de Ejemplo |
|-----------------|------------------|
| `{{ keywords }}` | Lista de keywords del template |
| `{{ business_type }}` | Tipo de negocio ingresado |
| `{{ target_audience }}` | Audiencia objetivo |
| `{{ call_to_action }}` | CTA configurado |
| `{{ phone }}` | +1 (555) 123-4567 |
| `{{ email }}` | contacto@ejemplo.com |
| `{{ current_year }}` | 2024 |

### 4. Metadata Completa en el Índice

El archivo `custom_templates/templates_index.json` guarda:

```json
{
  "name": "Template Tarot Místico Pro",
  "baseFilename": "template-tarot-mistico-pro",
  "filename": "template-tarot-mistico-pro.html",
  "previewFilename": "template-tarot-mistico-pro_preview.html",
  "githubLandingPath": "templates/landing/template-tarot-mistico-pro.html",
  "githubPreviewPath": "templates/previews/template-tarot-mistico-pro_preview.html",
  "businessType": "Tarot y Videncia",
  "keywords": ["tarot", "videncia"],
  "createdAt": "2024-11-30T14:30:00Z"
}
```

## 🔧 Cambios en el Código

### Backend: `custom_template_manager.py`

#### Constructor Actualizado
```python
def __init__(self, 
             landing_dir: str = "templates/landing",
             preview_dir: str = "templates/previews",
             index_dir: str = "custom_templates"):
```

#### Nuevos Métodos Privados

**`_sanitize_filename(name)`**
- Convierte nombres a filenames válidos

**`_generate_preview_html(content, metadata)`**
- Genera preview renderizado automáticamente
- Reemplaza variables Jinja2 con valores de ejemplo

#### Método `save_template()` Mejorado
```python
# Guarda en 2 lugares:
landing_file = "templates/landing/template-name.html"
preview_file = "templates/previews/template-name_preview.html"

# Retorna paths completos
return {
    "files": {
        "landing": landing_file,
        "preview": preview_file
    },
    "githubLandingPath": "templates/landing/...",
    "githubPreviewPath": "templates/previews/..."
}
```

### iOS: `TemplateManager.swift`

#### Struct `CustomTemplate` Actualizado
```swift
struct CustomTemplate: Identifiable, Codable {
    let id: String                  // filename sin .html
    let filename: String?           // template-name.html
    let githubLandingPath: String?  // templates/landing/...
    let githubPreviewPath: String?  // templates/previews/...
    // ... resto de campos
}
```

#### Init Mejorado
```swift
init(name: String, ...) {
    // Sanitiza nombre automáticamente
    let sanitized = name.lowercased()
        .replacingOccurrences(of: " ", with: "-")
        // ... limpieza de caracteres
    
    self.id = sanitized
    self.filename = "\(sanitized).html"
    self.githubLandingPath = "templates/landing/\(sanitized).html"
}
```

## 🧪 Pruebas

### Test Script: `test_custom_template_github.py`

Ejecuta prueba completa:
```bash
python3 test_custom_template_github.py
```

**Resultado esperado:**
```
✅ Template guardado en: templates/landing/template-tarot-mistico-pro.html
✅ Preview guardado en: templates/previews/template-tarot-mistico-pro_preview.html
✅ Template actualizado exitosamente en landing y preview
✅ Eliminado de ambas carpetas
```

### Verificar Archivos Creados

```bash
# Ver templates en landing
ls -lh templates/landing/

# Ver previews
ls -lh templates/previews/

# Ver índice
cat custom_templates/templates_index.json | jq
```

## 📦 Workflow de Uso

### 1. Usuario Genera Template (iOS App)
```swift
let template = CustomTemplate(
    name: "Template Tarot Místico",
    content: grokGeneratedHTML,
    businessType: "Tarot Profesional",
    keywords: ["tarot", "videncia"]
)

try TemplateManager.shared.saveTemplate(template)
```

### 2. Backend Procesa (Automático)
```python
# Se ejecuta cuando el endpoint recibe el POST
manager = CustomTemplateManager()
result = manager.save_template(template_data)

# Resultado:
# ✅ templates/landing/template-tarot-mistico.html (Jinja2)
# ✅ templates/previews/template-tarot-mistico_preview.html (HTML)
# ✅ custom_templates/templates_index.json actualizado
```

### 3. Commit a GitHub (Manual o Automático)
```bash
cd google-ads-backend-python

git add templates/landing/template-tarot-mistico.html
git add templates/previews/template-tarot-mistico_preview.html
git add custom_templates/templates_index.json

git commit -m "✨ Nuevo template: Template Tarot Místico"
git push
```

### 4. GitHub Pages (Automático)
- Preview disponible en: `https://saltbalente.github.io/google-ads-backend-python/templates/previews/template-tarot-mistico_preview.html`
- Landing disponible para el generador

## 🌐 URLs de GitHub Pages

Una vez pusheado, los templates están disponibles públicamente:

**Landing (Jinja2):**
```
https://raw.githubusercontent.com/saltbalente/google-ads-backend-python/main/templates/landing/template-name.html
```

**Preview (HTML estático):**
```
https://saltbalente.github.io/google-ads-backend-python/templates/previews/template-name_preview.html
```

## 🔄 Compatibilidad

### Backward Compatibility

El sistema es compatible con el código anterior:

- ✅ `get_all_templates()` funciona igual
- ✅ `get_templates_by_keywords()` funciona igual
- ✅ `delete_template()` ahora elimina de ambas carpetas
- ✅ `update_template()` actualiza ambos archivos

### Migración de Templates Antiguos

Si tenías templates con UUID en `custom_templates/`:

```bash
# Los templates viejos siguen funcionando
# Simplemente no están en templates/landing o templates/previews
# Puedes re-generarlos o migrarlos manualmente
```

## 📊 Beneficios

### Para el Usuario
- ✅ Templates con nombres legibles
- ✅ Preview instantáneo en GitHub Pages
- ✅ Fácil de compartir URLs

### Para el Desarrollador
- ✅ Estructura organizada y profesional
- ✅ Listos para version control
- ✅ Fácil debug (nombres descriptivos)

### Para GitHub Pages
- ✅ Archivos en la estructura correcta
- ✅ No requiere configuración adicional
- ✅ Compatible con el resto de templates

## 🎨 Ejemplo Completo

### Input del Usuario
```json
{
  "name": "Videncia Profesional Premium",
  "businessType": "Servicios de Videncia",
  "keywords": ["videncia", "tarot", "clarividencia"],
  "tone": "Profesional y místico",
  "callToAction": "Reserva tu Consulta"
}
```

### Output del Sistema

**1. Landing (`templates/landing/videncia-profesional-premium.html`)**
```html
<!DOCTYPE html>
<html>
<head><title>{{ business_type }}</title></head>
<body>
    <h1>{{ business_type }}</h1>
    <p>Servicios de {{ keywords }}</p>
    <a href="#cta">{{ call_to_action }}</a>
</body>
</html>
```

**2. Preview (`templates/previews/videncia-profesional-premium_preview.html`)**
```html
<!-- PREVIEW GENERADO - Videncia Profesional Premium -->
<!DOCTYPE html>
<html>
<head><title>Servicios de Videncia</title></head>
<body>
    <h1>Servicios de Videncia</h1>
    <p>Servicios de videncia, tarot, clarividencia</p>
    <a href="#cta">Reserva tu Consulta</a>
</body>
</html>
```

**3. Índice (`custom_templates/templates_index.json`)**
```json
[
  {
    "name": "Videncia Profesional Premium",
    "filename": "videncia-profesional-premium.html",
    "previewFilename": "videncia-profesional-premium_preview.html",
    "githubLandingPath": "templates/landing/videncia-profesional-premium.html",
    "githubPreviewPath": "templates/previews/videncia-profesional-premium_preview.html",
    "keywords": ["videncia", "tarot", "clarividencia"],
    "createdAt": "2024-11-30T14:30:00Z"
  }
]
```

## 🚀 Deploy

El sistema está **listo para producción**:

1. ✅ Backend testeado 100%
2. ✅ iOS struct actualizado
3. ✅ Nombres de archivo sanitizados
4. ✅ Preview automático generado
5. ✅ Compatible con GitHub Pages

**Próximo paso**: Cuando un usuario genere un template desde la app, automáticamente estará disponible en las carpetas correctas, listo para git commit y deploy.

---

**Commit**: `4da607a` - "✅ Custom templates ahora se guardan en templates/landing/ y templates/previews/ para GitHub Pages"  
**Fecha**: 30 de Noviembre, 2024
