# 📌 Pinterest URL Converter - Dashboard

Herramienta integrada en el dashboard principal para convertir URLs de Pinterest a URLs directas de imágenes.

## 🎯 Características

- ✅ **Conversión instantánea**: Transforma URLs de pines a URLs de imágenes en segundos
- 📱 **Responsive**: Funciona perfectamente en móvil y desktop
- 🎨 **UI minimalista**: Diseño limpio y profesional con gradientes modernos
- 📋 **Copia rápida**: Un clic para copiar la URL al portapapeles
- 🖼️ **Vista previa**: Muestra la imagen convertida antes de copiar
- 🔍 **Máxima calidad**: Extrae imágenes en resolución 1200x automáticamente

## 🚀 Uso

### Desde el Dashboard

1. Abre el dashboard principal: `https://tu-backend-url.com/`
2. En la categoría **Herramientas SEO**, haz clic en **Pinterest URL Converter**
3. Pega la URL del pin de Pinterest
4. Haz clic en **Convertir URL**
5. Copia la URL directa de la imagen

### Ejemplo

**URL de entrada:**
```
https://co.pinterest.com/pin/35606653299887146/
```

**URL de salida:**
```
https://i.pinimg.com/1200x/1b/50/bf/1b50bf166c7cd58dd27b4a337da5336b.jpg
```

## 🔧 Endpoint API

### POST `/api/pinterest/convert`

Convierte una URL de Pinterest a URL directa de imagen.

**Request:**
```json
{
  "url": "https://co.pinterest.com/pin/35606653299887146/"
}
```

**Response exitoso:**
```json
{
  "success": true,
  "pin_id": "35606653299887146",
  "pin_url": "https://co.pinterest.com/pin/35606653299887146/",
  "image_url": "https://i.pinimg.com/1200x/1b/50/bf/1b50bf166c7cd58dd27b4a337da5336b.jpg"
}
```

**Response con error:**
```json
{
  "success": false,
  "error": "URL de Pinterest inválida. Debe contener /pin/ID"
}
```

## 🛠️ Implementación Técnica

### Backend (Python + Flask)

```python
@app.route('/api/pinterest/convert', methods=['POST', 'OPTIONS'])
def pinterest_convert():
    # 1. Extrae el Pin ID de la URL usando regex
    # 2. Hace request a Pinterest con User-Agent
    # 3. Parsea HTML con BeautifulSoup
    # 4. Busca la imagen usando 3 métodos:
    #    - Meta tag og:image
    #    - Tags <img> con pinimg.com
    #    - Scripts con URLs de imágenes
    # 5. Optimiza la URL para máxima calidad (1200x)
    # 6. Retorna la URL directa
```

### Frontend (Vanilla JavaScript)

- Modal con animaciones suaves
- Estados de carga y error
- Validación de URLs
- Copy to clipboard API
- Responsive design con media queries

## 📦 Formatos de URL Soportados

✅ `https://co.pinterest.com/pin/XXXXXXXXXX/`
✅ `https://pinterest.com/pin/XXXXXXXXXX/`
✅ `https://www.pinterest.com/pin/XXXXXXXXXX/`
✅ `https://in.pinterest.com/pin/XXXXXXXXXX/`

## 🎨 Capturas

### Dashboard Principal
- Grid de herramientas por categorías
- Categoría "Herramientas SEO" destacada
- Diseño con gradientes púrpura

### Modal Converter
- Input para URL de Pinterest
- Botón de conversión con estados
- Vista previa de imagen
- URL en formato monospace
- Botón de copiar con feedback visual

## 🔄 Flujo de Trabajo

```
Usuario ingresa URL
    ↓
Backend extrae Pin ID
    ↓
Scraping de página de Pinterest
    ↓
Parsing HTML (BeautifulSoup)
    ↓
Extracción de URL de imagen
    ↓
Optimización de resolución (1200x)
    ↓
Respuesta con URL directa
    ↓
Frontend muestra imagen + URL
    ↓
Usuario copia URL
```

## 🚦 Estados de la UI

1. **Inicial**: Input vacío, listo para URL
2. **Loading**: Spinner + "Procesando..."
3. **Success**: Imagen + URL + Botón copiar
4. **Error**: Mensaje de error en amarillo
5. **Copiado**: Botón verde "✓ Copiado!"

## 🔐 Seguridad

- CORS habilitado para API
- Validación de formato de URL
- Timeout de 10s en requests
- Manejo de excepciones robusto
- User-Agent para evitar bloqueos

## 📈 Casos de Uso

1. **Diseñadores**: Extraer imágenes de alta calidad para proyectos
2. **Marketing**: Obtener assets de Pinterest para campañas
3. **Desarrollo**: Usar imágenes en landing pages
4. **SEO**: Analizar imágenes de competencia
5. **Content Creation**: Sourcing de imágenes

## 🔮 Futuras Mejoras

- [ ] Soporte para múltiples URLs en batch
- [ ] Descarga directa de imágenes
- [ ] Historial de conversiones
- [ ] Estadísticas de uso
- [ ] API key para rate limiting
- [ ] Conversión de boards completos

## 📝 Notas

- La calidad de imagen depende de la disponibilidad en Pinterest
- Algunas imágenes pueden tener marca de agua
- El scraping puede fallar si Pinterest cambia su estructura HTML
- Recomendado usar en desarrollo/staging, no para producción masiva

---

**Desarrollado con ❤️ para optimizar el flujo de trabajo**
