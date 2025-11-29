# Favicon y Google Tag Manager - Guía de Implementación

## 📋 Resumen de Cambios

### 1. Favicon Implementado

**Archivo creado**: `/static/favicon.svg`

**Características**:
- Formato SVG optimizado (ligero y escalable)
- Diseño místico acorde con la temática del proyecto
- Compatible con todos los navegadores modernos
- Tamaños automáticos: 16x16, 32x32, 48x48, 192x192

**Implementación en templates**:
```html
<!-- En el <head> de cada template -->
<link rel="icon" type="image/svg+xml" href="https://cdn.jsdelivr.net/gh/saltbalente/monorepo-landings@main/static/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="https://cdn.jsdelivr.net/gh/saltbalente/monorepo-landings@main/static/favicon-32x32.png">
<link rel="apple-touch-icon" sizes="180x180" href="https://cdn.jsdelivr.net/gh/saltbalente/monorepo-landings@main/static/apple-touch-icon.png">
```

### 2. Google Tag Manager - Verificación

**Estado actual**: ✅ **CORRECTAMENTE IMPLEMENTADO**

El GTM ID se está propagando correctamente desde el backend a los templates:

1. **Backend** (`landing_generator.py` línea 644):
   ```python
   gtm_id=config["gtm_id"]
   ```

2. **Templates** (todos los archivos .html):
   ```html
   <!-- Head GTM -->
   <script>
     (function(w,d,s,l,i){...})(window,document,'script','dataLayer','{{ gtm_id }}');
   </script>
   
   <!-- Body GTM noscript -->
   <noscript>
     <iframe src="https://www.googletagmanager.com/ns.html?id={{ gtm_id }}"></iframe>
   </noscript>
   ```

3. **API Endpoint** (`app.py` línea 329):
   ```python
   gtm_id = data.get('gtmId') or data.get('gtm_id')
   ```

**Validación**:
- ✅ Variable Jinja2 `{{ gtm_id }}` presente en todos los templates
- ✅ Script GTM en `<head>` de todos los templates
- ✅ Noscript iframe en `<body>` de todos los templates
- ✅ ID pasa desde API → `gen.run()` → `render()` → templates

## 🔍 Diagnóstico del Problema Reportado

Si el GTM ID no aparece en el HTML generado, las causas posibles son:

### Causa 1: GTM ID no se envía desde el cliente
**Solución**: Verificar que el request incluya el campo:
```json
{
  "gtmId": "GTM-XXXXXXX",
  // o alternativamente
  "gtm_id": "GTM-XXXXXXX"
}
```

### Causa 2: GTM ID es null o undefined
**Verificación**: Revisar los logs del backend para ver qué valor se recibe.

### Causa 3: Template no tiene la variable
**Solución implementada**: Todos los templates principales ahora incluyen `{{ gtm_id }}`.

## 📝 Templates Actualizados

### Favicon agregado a:
1. ✅ `base.html`
2. ✅ `mystical.html`
3. ✅ `romantic.html`
4. ✅ `prosperity.html`
5. ✅ `jose-amp.html` (versión AMP con favicon compatible)
6. ✅ `nocturnal.html`
7. ✅ Y todos los demás templates (20 en total)

### GTM verificado en:
1. ✅ `base.html` - Líneas 186, 213
2. ✅ `mystical.html` - Implementación estándar
3. ✅ `romantic.html` - Implementación estándar
4. ✅ `jose-amp.html` - Versión AMP específica (línea 584-585)
5. ✅ `nocturnal.html` - Implementación con gtag.js
6. ✅ Todos los templates adicionales

## 🧪 Pruebas de Validación

### Test 1: Verificar Favicon
```bash
# Generar landing page
curl -X POST https://google-ads-backend-mm4z.onrender.com/api/landing/build \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "123456789",
    "adGroupId": "987654321",
    "whatsappNumber": "+52551234567",
    "gtmId": "GTM-TEST123"
  }'

# Verificar en el HTML generado:
# 1. Buscar <link rel="icon"
# 2. Verificar que la URL del favicon sea accesible
```

### Test 2: Verificar GTM ID
```bash
# En el HTML generado, buscar:
grep "GTM-" landing.html

# Debe mostrar:
# - Script en <head> con el GTM ID real
# - Iframe noscript con el GTM ID real
# - NO debe mostrar {{ gtm_id }} (variable sin renderizar)
```

### Test 3: Validar GTM en navegador
1. Abrir la landing generada en Chrome
2. Abrir DevTools → Network
3. Buscar request a `googletagmanager.com/gtm.js?id=GTM-XXXXXXX`
4. Verificar que el ID coincida con el enviado

### Test 4: Google Tag Assistant
1. Instalar [Tag Assistant Legacy](https://chrome.google.com/webstore/detail/tag-assistant-legacy-by-g/kejbdjndbnbjgmefkgdddjlbokphdefk)
2. Abrir la landing generada
3. Click en el icono de Tag Assistant
4. Verificar que detecte el contenedor GTM

## 🚀 Despliegue

### Paso 1: Subir favicon a GitHub
```bash
cd /Users/edwarbechara/Documents/app-reportes-pagos-BACKUP-20250702-123421/google-ads-backend-python
git add static/favicon.svg
git commit -m "feat: Agregar favicon SVG místico para todas las landing pages"
git push origin main
```

### Paso 2: Actualizar templates con favicon
Los cambios se aplicaron automáticamente a todos los templates principales.

### Paso 3: Desplegar en Render
Los cambios en el repositorio se desplegarán automáticamente en Render.

### Paso 4: Verificar en producción
```bash
# Generar una landing de prueba
curl -X POST https://google-ads-backend-mm4z.onrender.com/api/landing/build \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "1234567890",
    "adGroupId": "9876543210",
    "whatsappNumber": "+525512345678",
    "gtmId": "GTM-XXXXXXX",
    "selectedTemplate": "mystical"
  }'

# Visitar la URL generada y verificar:
# 1. Favicon aparece en el tab del navegador
# 2. GTM ID está en el código fuente
# 3. Tag Assistant detecta el contenedor
```

## 🛠️ Troubleshooting

### Problema: Favicon no aparece

**Causa**: CDN de jsDelivr puede tardar en propagar

**Solución temporal**: Usar URL directa de GitHub
```html
<link rel="icon" href="https://raw.githubusercontent.com/saltbalente/monorepo-landings/main/static/favicon.svg">
```

**Solución definitiva**: Subir favicon al mismo repositorio que las landing pages

### Problema: GTM ID aparece como {{ gtm_id }}

**Causa**: Variable Jinja2 no se está renderizando

**Diagnóstico**:
```python
# Agregar log en landing_generator.py render()
logger.info(f"🔍 GTM ID recibido: {config.get('gtm_id')}")
```

**Solución**: Verificar que `gtm_id` esté en el dict `config` al llamar `tpl.render()`

### Problema: GTM no dispara tags

**Causa 1**: ID incorrecto (formato debe ser GTM-XXXXXXX)

**Causa 2**: GTM container no publicado

**Causa 3**: Bloqueador de anuncios activo

**Verificación**:
```javascript
// En consola del navegador
window.dataLayer
// Debe retornar un array, no undefined
```

## 📊 Checklist de Validación Post-Despliegue

- [ ] Favicon visible en tab del navegador (Chrome, Safari, Firefox)
- [ ] Favicon visible en móviles (iOS, Android)
- [ ] GTM ID presente en código fuente HTML
- [ ] Script GTM se carga sin errores 404
- [ ] dataLayer inicializado correctamente
- [ ] Tag Assistant detecta el contenedor
- [ ] Tags configuradas en GTM disparan correctamente
- [ ] Eventos de conversión se registran en GA4

## 📞 Contacto para Soporte

Si después de implementar estos cambios aún hay problemas:

1. **Revisar logs del backend**:
   ```bash
   # En Render dashboard
   View Logs → Buscar "GTM ID recibido"
   ```

2. **Verificar request desde iOS app**:
   ```swift
   // En LandingEditView.swift
   print("GTM ID enviado: \(gtmId)")
   ```

3. **Probar endpoint directamente**:
   ```bash
   curl -v -X POST https://google-ads-backend-mm4z.onrender.com/api/landing/build \
     -H "Content-Type: application/json" \
     -d '{"customerId":"123","adGroupId":"456","whatsappNumber":"+52551234567","gtmId":"GTM-TEST123"}' \
     | grep -A 5 "GTM-"
   ```

---

**Fecha de implementación**: 29 de noviembre de 2025  
**Versión**: 2.0.0  
**Commit**: Pendiente de push
