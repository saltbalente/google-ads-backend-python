# 🚀 Actualizar Variables en Render.com - SOLUCIÓN AL ERROR

## 🚨 Problema Identificado

El sistema en Render.com está fallando con el error:
```
GitHub repository verification failed: Repository not found
```

**Causa:** El `GITHUB_TOKEN` en Render.com es diferente al que funciona localmente.

## ✅ Solución Rápida

### Paso 1: Actualizar GITHUB_TOKEN en Render.com

1. **Ve a Render.com Dashboard:**
   - https://dashboard.render.com/
   - Selecciona tu servicio (landing page generator)

2. **Ve a Environment:**
   - Clic en **"Environment"** en el menú lateral

3. **Actualizar GITHUB_TOKEN:**
   - Busca la variable `GITHUB_TOKEN`
   - **Cambia el valor a:** `YOUR_GITHUB_TOKEN`
   - Clic **"Save Changes"**

### Paso 2: Redeploy el Servicio

1. Ve a la pestaña **"Manual Deploy"**
2. Clic **"Manual Deploy"** → **"Deploy latest commit"**
3. Espera a que termine el deployment

## 🔍 Verificar que Funciona

Después del redeploy, el sistema debería funcionar correctamente. Los logs deberían mostrar:

```
✅ Repository access successful!
📁 Repository: saltbalente/websitedinamico
🔒 Private: False
📤 Push permissions: True
🎉 GitHub configuration is ready!
```

En lugar del error anterior.

## 📋 Todas las Variables que Deben Estar en Render.com

Para referencia completa, estas son todas las variables que deben estar configuradas:

### GitHub
```
GITHUB_REPO_OWNER = saltbalente
GITHUB_REPO_NAME = websitedinamico
GITHUB_TOKEN = YOUR_GITHUB_TOKEN
```

### OpenAI
```
OPENAI_API_KEY = YOUR_OPENAI_API_KEY
OPENAI_MODEL = gpt-4o-mini
```

### DeepSeek
```
DEEPSEEK_API_KEY = YOUR_DEEPSEEK_API_KEY
DEEPSEEK_MODEL = deepseek-chat
```

### Google APIs
```
GOOGLE_API_KEY = AIzaSyBqBcCjr78Y33yxLHv2dbgPVKLW_xC6YXc
GOOGLE_ADS_DEVELOPER_TOKEN = Kqg431In6DxoZnSMJk0hQg
GOOGLE_ADS_CLIENT_ID = 82393641971-edkinpiigpprkbdi0dtnalem8ndo5c1j.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET = 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
GOOGLE_ADS_REFRESH_TOKEN = 1//05qNlWCfgnPRZCgYIARAAGAUSNwF-L9IrPwBJ2CdrABme75Bk-RUU-8WeYGiFsTkqatFijKG-ckHpqyfPRlQI68LTGWbN54JyUAY
GOOGLE_ADS_LOGIN_CUSTOMER_ID = 8531174172
```

### Vercel
```
VERCEL_TOKEN = MymrvqxzEZwJBiOpgvIcOF3U
VERCEL_PROJECT_ID = oFmmjcIB3CnHSTWW6hn09CO6
LANDINGS_BASE_DOMAIN = arcano.cloud
```

## 🧪 Script de Verificación

Ejecuta este comando para verificar todas las variables localmente:

```bash
python3 render_env_check.py
```

## ⚡ Resumen

**Problema:** Token de GitHub incorrecto en Render.com
**Solución:** Actualizar `GITHUB_TOKEN` y redeploy
**Tiempo estimado:** 2-3 minutos

¡Después de esto, el generador debería funcionar perfectamente! 🎉</content>
<parameter name="filePath">/Users/edwarbechara/Documents/app-reportes-pagos-BACKUP-20250702-123421/google-ads-backend-python/RENDER_FIX_README.md