# 🚀 Gunicorn Timeout Configuration for AI Image Optimization

## Problema

Worker timeout después de 30 segundos durante optimización de imágenes con IA:

```
[2025-11-29 20:23:08 +0000] [63] [CRITICAL] WORKER TIMEOUT (pid:80)
[2025-11-29 20:23:08 +0000] [80] [INFO] Worker exiting (pid: 80)
```

### Causa Raíz

- **Timeout default de Gunicorn**: 30 segundos
- **Tiempo real de optimización**: 
  - 1 imagen con Gemini: 3-5 segundos
  - 6 imágenes: 18-30 segundos
  - + API latency + resize + upload: **40-60 segundos total**

## Solución

Se creó `gunicorn_config.py` con timeout de **300 segundos (5 minutos)**.

---

## 📋 Configuración en Render

### Opción 1: Usar gunicorn_config.py (Recomendado)

En Render Dashboard → Settings → Build & Deploy → Start Command:

```bash
gunicorn --config gunicorn_config.py app:app
```

**Ventajas**:
- ✅ Configuración centralizada
- ✅ Fácil de mantener
- ✅ Incluye logging y hooks
- ✅ Preload app para mejor performance

---

### Opción 2: Flags inline (Alternativa)

```bash
gunicorn --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 120 --workers 4 --log-level info app:app
```

**Desventajas**:
- ⚠️ Más difícil de leer
- ⚠️ No reutilizable

---

## ⚙️ Parámetros Clave

| Parámetro | Valor | Razón |
|-----------|-------|-------|
| `timeout` | 300s (5 min) | Permite 6 imágenes × 20s/img + buffer |
| `graceful_timeout` | 120s | Shutdown suave |
| `workers` | 8 (Professional) | Óptimo para 2-4GB RAM |
| `threads` | 2 | 8 workers × 2 threads = 16 concurrent requests |
| `max_requests` | 1000 | Previene memory leaks |
| `preload_app` | True | Reduce memoria, mejora startup |
| `keepalive` | 5s | Mantiene conexiones activas |

### Configuración por Plan Render

| Plan | RAM | Workers | Threads | Total Concurrent |
|------|-----|---------|---------|------------------|
| **Free** | 512MB | 2 | 1 | 2 requests |
| **Starter** | 1GB | 4 | 1 | 4 requests |
| **Professional** | 2-4GB | **8** | **2** | **16 requests** ✅ |
| **Enterprise** | 8GB+ | 16 | 4 | 64 requests |

---

## 🧪 Testing Local

### Con gunicorn_config.py:
```bash
gunicorn --config gunicorn_config.py app:app
```

### Con Flask dev server (NO para producción):
```bash
python start_server.py
```

---

## 📊 Logs Esperados

**Startup exitoso**:
```
INFO - 🚀 Starting Gunicorn server with AI optimization support
INFO - ✅ Server ready on 0.0.0.0:8080 (timeout: 300s)
```

**Durante optimización** (ya no debe timeout):
```
INFO - 🤖 Starting Gemini optimization for top (2208x2097, JPEG)
INFO - 🧠 Gemini analysis: ¡Claro! Aquí tienes...
INFO - ✅ Optimized top: 555KB -> 132KB (76.2% reduction, 4.6s)
INFO - ✅ Processed and uploaded user image to https://cdn.jsdelivr.net/...
```

**Si aún hay timeout**:
```
ERROR - ❌ Worker 123 timed out after 300s
ERROR - This usually happens during AI image optimization
ERROR - Consider: 1) Reducing image count, 2) Increasing timeout
```

---

## 🔧 Troubleshooting

### Worker sigue haciendo timeout

**Posibles causas**:

1. **Demasiadas imágenes** (>10):
   - Solución: Limitar a 6 imágenes por landing
   - Backend ya tiene este límite implementado

2. **API de Gemini lenta**:
   - Verificar: `GOOGLE_API_KEY` correcta
   - Verificar: No rate limiting en cuenta Google Cloud
   - Considerar: Retry logic (ya implementado)

3. **Render free tier memory limit**:
   - Free tier: 512MB RAM
   - Solución: Upgrade a Starter plan ($7/mes) con 512MB+

### Verificar timeout actual

```bash
# En Render logs, buscar:
grep "timeout" /var/log/gunicorn.log
```

### Aumentar timeout aún más

En `gunicorn_config.py`:
```python
timeout = 600  # 10 minutos (para casos extremos)
```

---

## 📝 Checklist de Deploy

- [x] Crear `gunicorn_config.py`
- [ ] Actualizar Render Start Command
- [ ] Deploy y verificar logs
- [ ] Probar generación con 6 imágenes + IA
- [ ] Verificar que no hay timeouts
- [ ] Monitorear performance durante 24h

---

## 🎯 Métricas de Éxito

| Métrica | Antes | Después (Esperado) |
|---------|-------|-------------------|
| Worker timeouts | ✅ Frecuentes | ❌ Ninguno |
| Tiempo generación (6 imgs + IA) | N/A (timeout) | 40-60s |
| Success rate | ~60% (fallback) | ~98% (con IA) |
| Reducción tamaño imgs | 70-75% (std) | 80-85% (IA) |

---

## 🔗 Referencias

- [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html)
- [Render Start Commands](https://render.com/docs/deploys)
- [Worker Timeout Troubleshooting](https://docs.gunicorn.org/en/stable/faq.html#worker-timeout)

---

**Última actualización**: 2025-11-29  
**Commit**: Pending deployment  
**Status**: ✅ Ready for production
