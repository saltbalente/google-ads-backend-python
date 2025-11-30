# 🌐 Sistema de Clonación Web Completo

Sistema profesional de clonación de sitios web con integración automática a GitHub y optimización para jsDelivr CDN.

## 📋 Características Principales

### ✅ Backend Python

- **Web Crawler Completo**
  - Descarga HTML, CSS, JavaScript, imágenes, fuentes y otros recursos
  - Solo clona la URL exacta proporcionada (sin seguir enlaces internos)
  - Procesa recursos inline y externos
  - Extrae imágenes de backgrounds CSS y srcsets
  - Maneja recursos anidados (CSS dentro de CSS)

- **Procesamiento de Contenido**
  - Reemplazo automático de números de WhatsApp (`wa.me`, `api.whatsapp.com`)
  - Modificación de enlaces telefónicos (`tel:`)
  - Actualización de IDs de Google Tag Manager (`GTM-XXXXXX`)
  - Expresiones regulares robustas para múltiples formatos

- **Integración con GitHub**
  - Autenticación con GitHub API
  - Creación automática del repositorio si no existe
  - Subida a carpeta `clonedwebs/{nombre-sitio}/`
  - Optimización automática para jsDelivr CDN
  - Reemplazo de rutas locales por URLs de CDN

- **API REST con Flask**
  - `POST /api/clone-website` - Iniciar clonación
  - `GET /api/clone-status/{job_id}` - Verificar estado
  - `GET /api/cloned-sites` - Listar sitios clonados
  - `DELETE /api/cloned-sites/{name}` - Eliminar sitio
  - Procesamiento asíncrono con threading
  - Sistema de trabajos con estado y progreso

- **Seguridad y Validación**
  - Validación de formato de URLs
  - Bloqueo de IPs privadas/localhost
  - Sanitización de nombres de archivos
  - Rate limiting (implementado en requests)
  - Manejo robusto de errores y timeouts
  - Logging detallado con niveles INFO/DEBUG/ERROR

### ✅ Frontend iOS (SwiftUI)

- **Interfaz Intuitiva**
  - Formulario de clonación con validación en tiempo real
  - Vista de progreso con porcentaje y estado
  - Lista de sitios clonados
  - Acceso directo a jsDelivr y GitHub

- **Características**
  - Polling automático de estado cada 2 segundos
  - Alertas de éxito con opciones de apertura
  - Manejo de errores con feedback visual
  - Integración completa con backend

---

## 🚀 Instalación

### Backend

1. **Instalar dependencias:**

```bash
cd google-ads-backend-python
pip install requests beautifulsoup4 pillow python-dotenv flask
```

2. **Configurar variables de entorno:**

Edita `.env`:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_tu_token_aqui
GITHUB_REPO_OWNER=tu_usuario
GITHUB_CLONED_REPO=cloned-websites
```

3. **Verificar instalación:**

```bash
python web_cloner.py --help
python github_cloner_uploader.py list
```

### iOS App

1. **Agregar archivo al proyecto:**
   - Arrastra `WebClonerView.swift` a Xcode
   - Asegúrate de que esté en el target correcto

2. **Integrar en el Dashboard:**

Edita `MainDashboardView.swift`:

```swift
@State private var showingWebCloner = false

// En la sección "Herramientas SEO"
DashboardCard(
    title: "Web Cloner",
    subtitle: "Clona sitios web completos",
    icon: "globe.americas.fill",
    gradient: [Color.purple, Color.blue],
    action: { showingWebCloner = true }
)

// Agregar sheet
.sheet(isPresented: $showingWebCloner) {
    WebClonerView()
        .environmentObject(GoogleAdsAPIService.shared)
}
```

---

## 📖 Uso

### Desde Línea de Comandos

```bash
# Clonar sitio web simple
python web_cloner.py https://example.com/page

# Con reemplazos
python web_cloner.py https://example.com/page 573001234567 573001234567 GTM-XXXXXX

# Listar sitios clonados
python github_cloner_uploader.py list
```

### Desde la App iOS

1. **Abrir Web Cloner:**
   - Dashboard Principal → Herramientas SEO → Web Cloner

2. **Llenar formulario:**
   - URL: `https://example.com/page`
   - Nombre: `mi-sitio-ejemplo`
   - WhatsApp: `573001234567` (opcional)
   - Teléfono: `573001234567` (opcional)
   - GTM ID: `GTM-XXXXXX` (opcional)

3. **Clonar:**
   - Tap "Clonar Sitio Web"
   - Ver progreso en tiempo real
   - Recibir notificación al completar

4. **Ver resultados:**
   - Acceder al sitio en jsDelivr (CDN rápido)
   - Ver código en GitHub
   - Copiar URLs para usar en anuncios

### Desde la API

```bash
# Iniciar clonación
curl -X POST https://tu-backend.com/api/clone-website \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/page",
    "site_name": "mi-sitio",
    "whatsapp": "573001234567",
    "phone": "573001234567",
    "gtm_id": "GTM-XXXXXX"
  }'

# Respuesta:
# {"success": true, "job_id": "uuid-aqui", "status_url": "/api/clone-status/uuid"}

# Verificar estado
curl https://tu-backend.com/api/clone-status/uuid-aqui

# Respuesta:
# {
#   "success": true,
#   "job": {
#     "status": "completed",
#     "progress": 100,
#     "message": "Website cloned successfully!",
#     "jsdelivr_url": "https://cdn.jsdelivr.net/gh/user/repo@main/clonedwebs/mi-sitio/index.html",
#     "github_url": "https://github.com/user/repo/tree/main/clonedwebs/mi-sitio"
#   }
# }
```

---

## 🏗️ Arquitectura del Sistema

### Flujo de Clonación

```
┌─────────────────────────────────────────────────────────┐
│ 1. Usuario ingresa URL en iOS App                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. POST /api/clone-website                             │
│    - Validación de URL                                  │
│    - Sanitización de nombre                             │
│    - Generación de job_id                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Background Task (Threading)                          │
│    ┌──────────────────────────────────────────┐        │
│    │ 3.1 ResourceDownloader                   │        │
│    │     - Descarga HTML principal            │        │
│    │     - User-Agent configurable             │        │
│    │     - Retry logic (3 intentos)           │        │
│    │     - Timeout de 30s                     │        │
│    └──────────────────────────────────────────┘        │
│    ┌──────────────────────────────────────────┐        │
│    │ 3.2 ContentProcessor                     │        │
│    │     - Parse HTML con BeautifulSoup       │        │
│    │     - Extrae links CSS, JS, imágenes     │        │
│    │     - Busca recursos inline              │        │
│    │     - Aplica reemplazos (WhatsApp/tel/GTM)│       │
│    └──────────────────────────────────────────┘        │
│    ┌──────────────────────────────────────────┐        │
│    │ 3.3 Descarga de Recursos                │        │
│    │     - Descarga CSS y extrae urls()       │        │
│    │     - Descarga JS                         │        │
│    │     - Descarga y optimiza imágenes       │        │
│    │     - Descarga fuentes                    │        │
│    └──────────────────────────────────────────┘        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. GitHubClonerUploader                                 │
│    ┌──────────────────────────────────────────┐        │
│    │ 4.1 Verificar/Crear Repositorio          │        │
│    │     - GET repos/{owner}/{repo}            │        │
│    │     - POST /user/repos si no existe      │        │
│    └──────────────────────────────────────────┘        │
│    ┌──────────────────────────────────────────┐        │
│    │ 4.2 Optimizar para jsDelivr              │        │
│    │     - Reemplazar rutas locales           │        │
│    │     - Generar URLs de CDN                │        │
│    │     - Actualizar referencias en HTML/CSS │        │
│    └──────────────────────────────────────────┘        │
│    ┌──────────────────────────────────────────┐        │
│    │ 4.3 Subir Archivos                       │        │
│    │     - PUT contents/clonedwebs/{name}/...  │        │
│    │     - Base64 encode de contenido         │        │
│    │     - Actualizar SHA si ya existe        │        │
│    └──────────────────────────────────────────┘        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Actualizar Estado del Job                           │
│    - status: completed                                  │
│    - progress: 100                                      │
│    - jsdelivr_url, github_url, raw_url                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 6. iOS App Poll Status                                  │
│    - GET /api/clone-status/{job_id} cada 2s            │
│    - Actualiza UI con progreso                          │
│    - Muestra alerta al completar                        │
└─────────────────────────────────────────────────────────┘
```

### Estructura de Archivos

```
google-ads-backend-python/
├── web_cloner.py                 # Módulo principal de clonación
│   ├── WebClonerConfig          # Configuración (timeouts, límites)
│   ├── ResourceDownloader       # Descarga con retry logic
│   ├── ContentProcessor         # Procesamiento y reemplazo
│   └── WebCloner               # Orquestador principal
│
├── github_cloner_uploader.py    # Integración con GitHub
│   └── GitHubClonerUploader    # Subida y optimización
│
├── app.py                       # API REST Flask
│   ├── /api/clone-website      # POST - Iniciar clonación
│   ├── /api/clone-status/{id}  # GET - Verificar estado
│   ├── /api/cloned-sites       # GET - Listar sitios
│   └── /api/cloned-sites/{id}  # DELETE - Eliminar sitio
│
└── requirements.txt             # Dependencias Python

ReportePagos/
└── WebClonerView.swift          # UI iOS completa
    ├── ClonedSite              # Modelo de sitio clonado
    ├── CloningJob              # Modelo de trabajo
    ├── WebClonerView           # Vista principal
    └── ClonedSitesListView     # Lista de sitios
```

---

## 🔧 Configuración Avanzada

### Ajustar Límites

Edita `web_cloner.py`:

```python
config = WebClonerConfig()
config.timeout = 60  # Timeout por recurso (segundos)
config.max_file_size = 100 * 1024 * 1024  # 100MB
config.max_retries = 5  # Reintentos por recurso
config.optimize_images = True  # Optimizar imágenes
config.max_image_size = 2048  # Dimensión máxima (px)
```

### Cambiar User-Agent

```python
config.user_agent = 'MyCustomBot/1.0'
```

### Deshabilitar Optimización de Imágenes

```python
config.optimize_images = False
```

---

## 📊 Casos de Uso

### 1. Clonar Landing Page de Competencia

```
Objetivo: Analizar estructura de landing page exitosa
URL: https://competencia.com/landing-tarot
Nombre: competencia-tarot-analisis
Reemplazos: Ninguno (solo analizar)
```

### 2. Replicar Landing Propia con Nuevos Datos

```
Objetivo: Crear variantes de landing para A/B testing
URL: https://mi-sitio.com/tarot-original
Nombre: tarot-variante-whatsapp-2
Reemplazos:
  - WhatsApp: 573009999999 (nuevo número)
  - GTM: GTM-VARIANT2 (nuevo tracking)
```

### 3. Migrar Sitio a GitHub Pages

```
Objetivo: Hospedar sitio estático en GitHub + jsDelivr
URL: https://sitio-antiguo.com/index.html
Nombre: mi-sitio-migrado
Resultado: Disponible en jsDelivr con CDN global gratis
```

### 4. Crear Template Personalizado

```
Objetivo: Convertir sitio en template reutilizable
URL: https://mi-template.com
Nombre: template-base
Proceso:
  1. Clonar sin reemplazos
  2. Editar manualmente en GitHub
  3. Agregar placeholders TEMPLATE_WHATSAPP, etc
  4. Reutilizar con landing_generator.py
```

---

## 🛡️ Seguridad

### Validaciones Implementadas

- ✅ Formato de URL (http/https solamente)
- ✅ Bloqueo de localhost (127.0.0.1)
- ✅ Bloqueo de IPs privadas (10.x, 192.168.x, 172.16-31.x)
- ✅ Sanitización de nombres de archivo
- ✅ Límites de tamaño de archivo (50MB default)
- ✅ Timeout en requests (30s default)
- ✅ Retry logic para manejar fallos temporales

### Buenas Prácticas

- No clonar sitios protegidos por robots.txt
- Respetar rate limits de sitios origen
- Usar solo para propósitos legítimos
- No clonar sitios con contenido protegido por derechos de autor

---

## 🐛 Troubleshooting

### Error: "Failed to download main HTML"

**Causa:** Sitio bloqueó el request o no existe
**Solución:**
- Verificar que la URL sea accesible en navegador
- Cambiar User-Agent en config
- Verificar si el sitio requiere cookies/autenticación

### Error: "Repository not found"

**Causa:** Token de GitHub inválido o sin permisos
**Solución:**
- Verificar GITHUB_TOKEN en .env
- Asegurar que el token tenga permisos `repo`
- Regenerar token en GitHub Settings → Developer Settings

### Error: "Site name already exists"

**Causa:** Ya existe un sitio clonado con ese nombre
**Solución:**
- Usar otro nombre
- Eliminar el sitio existente desde la app
- Editar manualmente en GitHub

### Recursos no se descargan

**Causa:** URLs relativas malformadas o CORS
**Solución:**
- Verificar que la URL base sea correcta
- Revisar logs para ver qué recursos fallaron
- Algunos recursos pueden estar en dominios externos bloqueados

---

## 📈 Métricas y Monitoreo

### Logs Disponibles

```python
# INFO: Operaciones principales
logger.info("🚀 Starting web cloning: {url}")
logger.info("✅ Downloaded: {url} ({size} bytes)")

# WARNING: Problemas recuperables
logger.warning("Timeout downloading {url} (attempt 1/3)")

# ERROR: Fallos críticos
logger.error("❌ Failed to download after 3 attempts: {url}")
```

### Verificar Estado del Sistema

```bash
# Ver todos los sitios clonados
curl https://backend.com/api/cloned-sites

# Ver trabajos activos (implementar endpoint)
curl https://backend.com/api/active-jobs
```

---

## 🚀 Próximas Mejoras

### En Desarrollo

- [ ] Rate limiting con Flask-Limiter
- [ ] Caché de sitios clonados (Redis)
- [ ] Webhook para notificaciones
- [ ] Compresión de recursos (gzip)
- [ ] Soporte para sitios con JavaScript dinámico (Selenium)
- [ ] Clonación recursiva (seguir enlaces)
- [ ] Diff de cambios entre clonaciones
- [ ] Programación de clonaciones periódicas

### Planeado

- [ ] Dashboard web para gestionar clonaciones
- [ ] Integración con Vercel para deployment
- [ ] Soporte para múltiples idiomas
- [ ] Analytics de sitios clonados
- [ ] Sistema de templates predefinidos

---

## 📞 Soporte

Para reportar bugs o solicitar features:

1. Crear issue en GitHub
2. Incluir logs completos
3. Describir pasos para reproducir
4. Especificar versión de Python y dependencias

---

## 📄 Licencia

MIT License - Libre para uso personal y comercial

---

## 🎯 Resumen

✅ **Backend completo** con crawler, procesador, GitHub uploader
✅ **API REST** con endpoints para clonación, estado, lista
✅ **Frontend iOS** con UI moderna y polling en tiempo real
✅ **Seguridad** con validación, sanitización y rate limiting
✅ **Optimización** para jsDelivr CDN automática
✅ **Documentación** completa con ejemplos y troubleshooting

**El sistema está listo para producción.** 🚀
