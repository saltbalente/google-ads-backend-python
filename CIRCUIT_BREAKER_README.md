# 🛡️ Circuit Breaker System - Sistema de Protección de Presupuesto

## 📋 Descripción

Sistema automático que monitorea el gasto de campañas de Google Ads y las pausa automáticamente cuando detecta gastos anormales, protegiéndote de perder presupuesto por errores o picos inesperados.

## 🎯 Características

- ✅ **Monitoreo Automático**: Revisa todas las campañas cada 30 minutos
- ✅ **Pausa Inteligente**: Detiene campañas que exceden límites configurados
- ✅ **Notificaciones**: Avisa inmediatamente cuando se activa
- ✅ **Auto-Reactivación**: Reanuda campañas después de 1 hora de enfriamiento
- ✅ **Trabajo 24/7**: Funciona continuamente sin intervención
- ✅ **Multi-Cuenta**: Soporta múltiples cuentas con límites independientes

## 🏗️ Arquitectura

```
Backend (Render) - Trabajo Continuo
├── Flask API (Endpoints REST)
├── APScheduler (Scheduler de tareas)
├── SQLite Database (Estado y historial)
└── Google Ads API (Acciones y métricas)

iOS App - Configuración
└── CircuitBreakerConfigView (UI de configuración)
```

## 💾 Base de Datos

### Tablas Creadas Automáticamente

**account_limits**: Límites por cuenta
- customer_id
- max_spend_per_hour_cop (default: 300,000 COP)
- max_spend_per_day_cop (default: 2,000,000 COP)
- enabled

**monitored_campaigns**: Campañas bajo monitoreo
- customer_id
- campaign_id
- campaign_name
- status (ACTIVE, PAUSED_BY_CB)

**circuit_breaker_events**: Historial de acciones
- customer_id
- campaign_id
- event_type (PAUSED, RESUMED)
- reason
- spend_amount_cop
- threshold_cop
- timestamp

**spend_history**: Historial de gasto por hora
- customer_id
- campaign_id
- hour_timestamp
- spend_usd
- spend_cop
- impressions, clicks, conversions

## 🔧 Configuración Backend

### 1. Variables de Entorno en Render

```bash
# Google Ads API
GOOGLE_ADS_DEVELOPER_TOKEN=tu_developer_token
GOOGLE_ADS_CLIENT_ID=tu_client_id
GOOGLE_ADS_CLIENT_SECRET=tu_client_secret
GOOGLE_ADS_REFRESH_TOKEN=tu_refresh_token
GOOGLE_ADS_LOGIN_CUSTOMER_ID=tu_mcc_id

# Circuit Breaker (opcional)
CIRCUIT_BREAKER_DB=circuit_breaker.db
NOTIFICATION_WEBHOOK=https://hooks.slack.com/... # Para notificaciones
```

### 2. Instalación de Dependencias

```bash
pip install APScheduler==3.10.4
```

### 3. Archivos Necesarios

- `circuit_breaker.py` - Sistema completo de Circuit Breaker
- Integración en `app.py` - Ya incluida automáticamente

## 📱 API Endpoints

### POST /api/circuit-breaker/accounts
Agregar cuenta al monitoreo

**Request:**
```json
{
  "customer_id": "1234567890",
  "max_spend_per_hour_cop": 300000,
  "max_spend_per_day_cop": 2000000
}
```

### POST /api/circuit-breaker/campaigns
Agregar campaña específica

**Request:**
```json
{
  "customer_id": "1234567890",
  "campaign_id": "987654321",
  "campaign_name": "Mi Campaña"
}
```

### GET /api/circuit-breaker/status
Obtener estado del sistema

**Response:**
```json
{
  "success": true,
  "accounts_monitored": 5,
  "campaigns_monitored": 23,
  "events_last_24h": 3,
  "status": "active"
}
```

## 🚀 Cómo Usar

### Desde la App iOS

1. Ir a configuración de cuenta
2. Abrir "Circuit Breaker / Protección de Presupuesto"
3. Configurar límites:
   - Límite por hora (ej: 300,000 COP)
   - Límite por día (ej: 2,000,000 COP)
4. Activar protección
5. ¡Listo! El sistema monitoreará automáticamente

### Desde API (Programático)

```python
import requests

# Activar para una cuenta
response = requests.post(
    "https://google-ads-backend-mm4z.onrender.com/api/circuit-breaker/accounts",
    json={
        "customer_id": "1234567890",
        "max_spend_per_hour_cop": 300000
    }
)
```

## ⏰ Ciclo de Monitoreo

```
Cada 30 minutos:
1. Obtener todas las campañas monitoreadas
2. Para cada campaña:
   - Consultar gasto de la última hora
   - Comparar con límite configurado
   - Si excede → Pausar + Notificar + Registrar evento
3. Verificar campañas pausadas:
   - Si pasó 1 hora → Reanudar + Notificar

Ejemplo de Timeline:
10:00 - Campaña gasta $350,000 COP en 1 hora
10:30 - Circuit Breaker detecta exceso → PAUSA
10:30 - Notificación enviada
11:30 - Cooldown completado → REANUDA
11:30 - Notificación de reactivación
```

## 📊 Lógica de Detección

```python
if spend_last_hour > max_spend_per_hour:
    pause_campaign()
    send_notification()
    schedule_resume(in_1_hour)
```

## 🔔 Notificaciones

### Configurar Webhook (Opcional)

**Slack:**
```bash
NOTIFICATION_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Discord:**
```bash
NOTIFICATION_WEBHOOK=https://discord.com/api/webhooks/YOUR/WEBHOOK
```

**Telegram:**
Implementar custom endpoint en `send_notification()`

### Formato de Notificación

```
⚠️ Circuit Breaker Activado
Campaña 'Amarres de Amor - Principal' pausada automáticamente

• Customer ID: 1234567890
• Campaign ID: 987654321
• Gasto: $350,000 COP
• Límite: $300,000 COP
• Reactivación: 11:30
```

## 🛠️ Mantenimiento

### Ver Logs del Sistema

```bash
# En Render Dashboard
Ver logs en tiempo real para monitorear:
"🔍 Circuit Breaker check running..."
"✅ Circuit Breaker check completed"
"🚨 CIRCUIT BREAKER TRIGGERED: Nombre Campaña"
```

### Consultar Base de Datos

```python
import sqlite3

conn = sqlite3.connect('circuit_breaker.db')
cursor = conn.cursor()

# Ver eventos recientes
cursor.execute("""
    SELECT * FROM circuit_breaker_events 
    ORDER BY timestamp DESC LIMIT 10
""")
print(cursor.fetchall())
```

## 🔐 Seguridad

- ✅ Base de datos SQLite con persistencia en Render
- ✅ Credenciales en variables de entorno
- ✅ No expone tokens en endpoints públicos
- ✅ Solo modifica status de campañas (no borra datos)

## 📈 Optimizaciones Recomendadas

### Cambiar Frecuencia de Monitoreo

```python
# En circuit_breaker.py, línea del scheduler:
scheduler.add_job(
    func=monitor_all_campaigns,
    trigger=IntervalTrigger(minutes=15),  # Cambiar de 30 a 15 min
    ...
)
```

### Ajustar Tiempo de Cooldown

```python
# En check_paused_campaigns():
one_hour_ago = datetime.utcnow() - timedelta(hours=2)  # Cambiar de 1 a 2 horas
```

## 🧪 Testing

### 1. Test Local (Sin pausar realmente)

Modificar temporalmente `pause_campaign()`:
```python
def pause_campaign(client, customer_id: str, campaign_id: str) -> bool:
    print(f"[TEST MODE] Would pause campaign {campaign_id}")
    return True  # Simular éxito
```

### 2. Test con Campaña Real

1. Configurar límite muy bajo (ej: 1,000 COP)
2. Esperar el siguiente ciclo de monitoreo
3. Verificar en logs si detecta exceso
4. Confirmar pausa en Google Ads

## ❓ FAQs

**P: ¿Qué pasa si el backend se cae?**
R: Al reiniciar, retoma el monitoreo. Las campañas pausadas se reanudarán en el siguiente ciclo.

**P: ¿Puedo pausar el monitoreo temporalmente?**
R: Sí, set `enabled = 0` en la tabla `account_limits` para esa cuenta.

**P: ¿Funciona con campañas nuevas?**
R: Sí, agrega campañas automáticamente al activar protección para la cuenta.

**P: ¿Consume mucho de la API de Google Ads?**
R: Cada chequeo hace 2 queries por campaña. Con 50 campañas = 100 queries cada 30 min = 4,800/día (bien dentro del límite diario).

## 🎉 Beneficios

- 💰 Protege presupuesto de gastos inesperados
- 🤖 Funciona automáticamente 24/7
- 📱 No depende de tener la app abierta
- ⚡ Reacción rápida (máximo 30 min delay)
- 📊 Historial completo de eventos
- 🔔 Notificaciones instantáneas
- 🔄 Auto-recuperación después de cooldown

## 📞 Soporte

Si el Circuit Breaker no funciona:
1. Verificar logs en Render Dashboard
2. Confirmar que APScheduler está corriendo
3. Revisar variables de entorno
4. Verificar conectividad con Google Ads API
5. Consultar tabla `circuit_breaker_events` para errores
