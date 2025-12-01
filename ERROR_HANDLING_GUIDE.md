# 🚨 Guía de Manejo de Errores - Sistema P0+P1

## 📋 Índice de Posibles Fallos

### 1. Errores de API (OpenRouter/Grok)

#### Error 401: API Key Inválida
**Causa:** API key incorrecta o no configurada
```json
{
  "success": false,
  "error": "OpenRouter API key not configured"
}
```
**Solución:**
- Verificar variable `OPEN_ROUTER_API_KEY` en Render
- Revisar que la key no esté expirada
- Regenerar key en OpenRouter si es necesario

**Prevención implementada:**
```python
# app.py línea 1107
api_key = os.getenv('OPEN_ROUTER_API_KEY') or os.getenv('OPENROUTER_API_KEY')
if not api_key:
    return None, 'OpenRouter API key not configured'
```

---

#### Error 429: Rate Limit Excedido
**Causa:** Demasiadas peticiones en corto tiempo
```json
{
  "success": false,
  "error": "OpenRouter error 429: Rate limit exceeded"
}
```
**Solución automática:**
- Sistema hace retry con backoff exponencial (2s, 4s, 8s)
- Después de 3 intentos, activa fallback local con BeautifulSoup

**Prevención implementada:**
```python
# Retry automático línea 1140
if resp.status_code in [429, 500, 502, 503, 504] and attempt < max_retries:
    continue  # Retry con backoff
```

---

#### Error 500/502/503/504: Error del Servidor
**Causa:** OpenRouter/Grok tiene problemas internos
```json
{
  "success": false,
  "error": "OpenRouter error 500: Internal server error"
}
```
**Solución automática:**
1. Retry automático (3 intentos)
2. Fallback a OpenAI si está configurado
3. Fallback local con BeautifulSoup

**Prevención implementada:**
```python
# Cadena de fallbacks línea 1425-1460
# 1. OpenRouter → 2. OpenAI → 3. BeautifulSoup Local
```

---

#### Timeout: Respuesta Tardía
**Causa:** Template muy grande o servidor lento
```json
{
  "success": false,
  "error": "OpenRouter request timeout (60s)"
}
```
**Solución automática:**
- Retry con timeout aumentado: 30s → 60s → 90s → 120s
- Si falla, usa fallback local

**Prevención implementada:**
```python
# Timeout dinámico línea 1380-1390
if effective_size > 20000:
    ai_timeout = 90
elif effective_size > 10000:
    ai_timeout = 60
else:
    ai_timeout = 30
```

---

#### Respuesta Malformada
**Causa:** API devuelve JSON inválido o estructura incorrecta
```json
{
  "success": false,
  "error": "Invalid OpenRouter response structure: KeyError 'choices'"
}
```
**Solución automática:**
- Sistema intenta parsear con try/except
- Si falla, activa fallback local

**Prevención implementada:**
```python
# Línea 1150
try:
    content = data['choices'][0]['message']['content']
except Exception as e:
    return None, f'Invalid response: {str(e)}'
```

---

### 2. Errores de Validación (P0)

#### Template Demasiado Grande
**Causa:** HTML >150KB
```json
{
  "success": false,
  "error": "Template too large (180KB). Maximum: 150KB",
  "validation": "size_limit",
  "size": 184320
}
```
**Solución:**
1. Sistema activa extracción de secciones (reduce 92%)
2. Si aún es muy grande, solicitar al usuario reducir template

**Frontend muestra:**
```
❌ Template demasiado grande (180KB, máx: 150KB)
```

---

#### HTML Inválido
**Causa:** Falta `<html>` o `<!DOCTYPE>`
```json
{
  "success": false,
  "error": "Invalid HTML structure: missing <html> or <!DOCTYPE>",
  "validation": "html_structure"
}
```
**Frontend muestra:**
```
❌ HTML inválido o incompleto
```

---

#### Instrucciones Muy Cortas
**Causa:** Menos de 10 caracteres
```json
{
  "success": false,
  "error": "Instructions too short (5 chars). Minimum: 10 characters",
  "validation": "instruction_length"
}
```
**Frontend muestra:**
```
❌ Instrucciones muy cortas (mín: 10 caracteres)
```

---

#### Operación Peligrosa Detectada
**Causa:** Palabras como "elimina todo", "borra el template"
```json
{
  "success": false,
  "error": "Dangerous operation not allowed: \"elimina todo\"",
  "validation": "dangerous_operation",
  "pattern": "elimina todo"
}
```
**Frontend muestra:**
```
❌ Operación peligrosa detectada
```

---

### 3. Errores de Red

#### Sin Conexión a Internet
**Frontend (Swift):**
```swift
// Error: The Internet connection appears to be offline
```
**Solución:**
- Mostrar alerta al usuario
- Sugerir verificar conexión
- Habilitar modo offline (solo edición local)

---

#### DNS No Resuelve
**Backend:**
```
ConnectionError: Failed to resolve 'openrouter.ai'
```
**Solución automática:**
- Retry con backoff
- Fallback a OpenAI (diferente dominio)
- Fallback local

---

#### Firewall/Proxy Bloqueando
**Backend:**
```
ConnectionError: Connection refused
```
**Solución:**
- Verificar que Render permite conexiones salientes
- Revisar que no haya IP bans

---

### 4. Errores de GitHub (Guardado)

#### Token Expirado o Inválido
```json
{
  "success": false,
  "error": "GitHub authentication failed: 401 Unauthorized"
}
```
**Solución:**
- Regenerar GitHub token
- Actualizar variable `GITHUB_TOKEN` en Render

**Frontend muestra:**
```
❌ Error al guardar: Token de GitHub inválido
```

---

#### Repositorio No Encontrado
```json
{
  "success": false,
  "error": "Repository not found: 404"
}
```
**Solución:**
- Verificar que `GITHUB_REPO_OWNER` y `GITHUB_REPO_NAME` sean correctos
- Verificar que el token tenga permisos de escritura

---

#### Conflicto de Merge
```json
{
  "success": false,
  "error": "Merge conflict detected"
}
```
**Solución automática:**
- Sistema sobrescribe con la versión más reciente
- Usuario puede ver versiones previas en historyStack

---

### 5. Errores de Memoria/Recursos

#### Out of Memory (Render)
**Síntoma:** Server se reinicia inesperadamente
```
MemoryError: Unable to allocate array
```
**Solución:**
1. Usar extracción de secciones (reduce 92% memoria)
2. Aumentar plan de Render si es recurrente
3. Implementar límite de templates simultáneos

**Prevención implementada:**
```python
# Caché LRU máximo 100 templates
@lru_cache(maxsize=100)
def get_cached_template_sections(template_id):
```

---

#### Disco Lleno (Versionado)
**Causa:** Demasiadas versiones guardadas
```
OSError: [Errno 28] No space left on device
```
**Solución automática:**
```python
# Línea con cleanup_old_versions()
# Mantiene máximo 20 versiones por template
if len(versions) > 20:
    versions_to_delete = versions[20:]
    for old_version in versions_to_delete:
        os.remove(old_version)
```

---

### 6. Errores de Frontend (Swift)

#### UI Freeze Durante Transformación
**Causa:** Operación bloqueando MainThread
**Solución implementada:**
```swift
// Todas las llamadas de red usan Task y await
Task {
    defer { isSaving = false }
    // ... operación asíncrona
}
```

---

#### Crash por Force Unwrap
**Causa:** Optional no manejado
```swift
// ❌ MAL
let url = URL(string: backendURL)!

// ✅ BIEN (implementado)
guard let url = URL(string: "\(backendURL)/api/...") else {
    validationMessage = "❌ Error: URL inválida"
    showValidationAlert = true
    return
}
```

---

#### Estado Inconsistente
**Causa:** Updates de UI fuera de MainActor
**Solución implementada:**
```swift
await MainActor.run {
    self.sourceCode = transformedCode
    self.showEditor = false
}
```

---

### 7. Errores de BeautifulSoup (Fallback Local)

#### HTML No Parseable
**Causa:** HTML severamente corrupto
```python
ParserError: Document is empty
```
**Solución:**
- Devolver error al usuario
- Solicitar que verifique el HTML manualmente

---

#### Selector No Encontrado
**Causa:** Template no tiene estructura esperada
```python
# Busca botones pero no hay ninguno
buttons = soup.find_all('button')
if not buttons:
    # Crea nuevos elementos en lugar de modificar existentes
```

---

### 8. Errores de Cache

#### Cache Corrupto
**Causa:** Pickle no puede deserializar
```python
PickleError: invalid load key
```
**Solución automática:**
```python
try:
    cached = get_cached_template_sections(template_id)
except:
    # Regenerar cache desde disco
    cached = None
```

---

### 9. Errores de Markdown Limpieza

#### Código No Limpiado Correctamente
**Síntoma:** HTML envuelto en ```html ... ```
**Solución implementada:**
```python
# Método 1: Regex
m = re.search(r"```(?:html)?\s*\n([\s\S]*?)\n```", transformed)
# Método 2: Split por líneas
if transformed.strip().startswith('```'):
    lines = transformed.strip().split('\n')
    # Elimina primera y última línea
```

**Validación post-limpieza:**
```python
if not ('<html' in transformed.lower() or '<!doctype' in transformed.lower()):
    logger.warning("Cleaned response invalid, reverting")
    transformed = original_transformed
```

---

## 🛡️ Sistema de Fallbacks (Orden de Ejecución)

```
┌─────────────────────────────────────────┐
│  1. Validación Pre-envío (P0)           │
│     ├─ Tamaño < 150KB                   │
│     ├─ HTML válido                      │
│     ├─ Instrucciones > 10 chars         │
│     ├─ Sin operaciones peligrosas       │
│     └─ Campos requeridos presentes      │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  2. Extracción de Secciones (P1)        │
│     └─ Reduce payload 92% si es grande  │
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  3. Fallback Local PRIMERO (P1)         │
│     └─ BeautifulSoup cubre 90% casos    │
└─────────────────────────────────────────┘
                   ↓ (si no aplica)
┌─────────────────────────────────────────┐
│  4. OpenRouter/Grok con Retry           │
│     ├─ Intento 1: timeout dinámico      │
│     ├─ Intento 2: +30s timeout          │
│     └─ Intento 3: +30s timeout          │
└─────────────────────────────────────────┘
                   ↓ (si falla)
┌─────────────────────────────────────────┐
│  5. OpenAI Fallback con Retry           │
│     └─ Mismo sistema de retry            │
└─────────────────────────────────────────┘
                   ↓ (si falla)
┌─────────────────────────────────────────┐
│  6. Fallback Local Mejorado (P1)        │
│     └─ BeautifulSoup más agresivo       │
└─────────────────────────────────────────┘
                   ↓ (si falla)
┌─────────────────────────────────────────┐
│  7. Error Final al Usuario              │
│     └─ Con mensaje descriptivo          │
└─────────────────────────────────────────┘
```

---

## 📊 Tabla de Códigos de Error

| Código | Tipo | Severidad | Auto-Recovery |
|--------|------|-----------|---------------|
| 400 | Validación | Media | ❌ (usuario debe corregir) |
| 401 | Auth | Alta | ❌ (admin debe reconfigurar) |
| 403 | Forbidden | Alta | ❌ (operación no permitida) |
| 404 | Not Found | Media | ⚠️ (verificar config) |
| 429 | Rate Limit | Baja | ✅ (retry automático) |
| 500 | Server Error | Media | ✅ (retry + fallback) |
| 502 | Bad Gateway | Baja | ✅ (retry automático) |
| 503 | Service Unavailable | Baja | ✅ (retry automático) |
| 504 | Gateway Timeout | Media | ✅ (retry + fallback) |
| Timeout | Red | Media | ✅ (retry con más tiempo) |
| ConnectionError | Red | Alta | ✅ (fallback local) |

---

## 🔍 Monitoreo y Debugging

### Logs Importantes a Revisar

**✅ Éxito:**
```
✅ Validation passed - proceeding with transformation
✅ Using cached sections for: template-id
✅ Local transformation successful (no AI needed)
✅ OpenRouter successful on attempt 1
✅ Template guardado exitosamente en GitHub
```

**⚠️ Advertencias:**
```
⚠️ OpenRouter failed: Rate limit exceeded
⚠️ Could not save version: Permission denied
⚠️ Cleaned response invalid, reverting
```

**❌ Errores:**
```
❌ Template too large: 180KB (max: 150KB)
❌ All transformation methods failed
❌ Final OpenAI attempt also failed
```

---

## 🚀 Comandos de Diagnóstico

### Verificar Estado del Backend
```bash
curl https://google-ads-backend-mm4z.onrender.com/health
```

### Test Manual de Endpoint
```bash
curl -X POST https://google-ads-backend-mm4z.onrender.com/api/templates/transform/patch \
  -H "Content-Type: application/json" \
  -d '{
    "code": "<!DOCTYPE html><html><body><h1>Test</h1></body></html>",
    "instructions": "Cambia el título a Hola Mundo"
  }'
```

### Ver Logs en Tiempo Real (Render)
```
1. Dashboard → Servicios → google-ads-backend
2. Logs → Enable Auto-refresh
3. Filtrar por "ERROR" o "❌"
```

---

## 📞 Matriz de Respuestas Rápidas

### "No funciona nada"
1. ✅ ¿Backend está online? → curl /health
2. ✅ ¿Variable OPEN_ROUTER_API_KEY configurada?
3. ✅ ¿Logs muestran errores?

### "Muy lento (>60s)"
1. ✅ ¿Template es muy grande? → Verificar tamaño
2. ✅ ¿Extracción de secciones activada? → Ver logs
3. ✅ ¿OpenRouter respondiendo lento? → Usar fallback local

### "Error al guardar en GitHub"
1. ✅ ¿Token válido? → Regenerar si expiró
2. ✅ ¿Repositorio existe? → Verificar owner/name
3. ✅ ¿Permisos correctos? → Token debe tener repo:write

### "Respuesta extraña de IA"
1. ✅ ¿Markdown limpiado? → Ver logs "Cleaned markdown"
2. ✅ ¿HTML válido después? → Validación post-limpieza
3. ✅ ¿Usar fallback local? → Más predecible

---

## ✅ Checklist de Troubleshooting

- [ ] Backend está online y responde a /health
- [ ] Variable OPEN_ROUTER_API_KEY configurada en Render
- [ ] Logs no muestran errores críticos (❌)
- [ ] Template < 150KB o extracción activada
- [ ] Instrucciones > 10 caracteres
- [ ] HTML válido con <html> y </html>
- [ ] GitHub token válido y con permisos
- [ ] Frontend puede conectarse al backend
- [ ] Timeout adecuado para tamaño del template
- [ ] Fallback local funciona independientemente

---

**Última actualización:** 1 de diciembre de 2025
