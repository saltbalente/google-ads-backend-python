# Google Ads Backend API - Python

Backend en Python + Flask para crear anuncios en Google Ads usando gRPC.

## ¿Por qué Python?

La librería oficial `google-ads` de Python tiene soporte completo y estable para gRPC, mientras que `google-ads-api` de Node.js tiene problemas de compatibilidad.

## Funcionamiento Comprobado

✅ **PROBADO Y FUNCIONANDO** - Se creó exitosamente un anuncio de prueba:
```
Resource Name: customers/5753767756/adGroupAds/166462715675~784188257211
```

## Deployment en Vercel

Vercel soporta Python usando Serverless Functions.

### Pasos:

1. Instalar Vercel CLI:
```bash
npm install -g vercel
```

2. Deploy:
```bash
cd google-ads-backend-python
vercel
```

3. Configurar variables de entorno en Vercel dashboard
4. Actualizar URL en la app iOS

## Ejecutar Localmente

```bash
pip3 install -r requirements.txt
python3 app.py
```

El servidor estará en: http://localhost:5000

## Endpoints

- `GET /api/health` - Estado del servidor
- `POST /api/create-ad` - Crear anuncio

## Test

```bash
curl -X POST http://localhost:5000/api/create-ad \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "5753767756",
    "adGroupId": "166462715675",
    "headlines": ["Test 1", "Test 2", "Test 3"],
    "descriptions": ["Desc 1", "Desc 2"],
    "finalUrl": "https://www.example.com"
  }'
```

##  Solución Final

Este backend en Python reemplaza al de Node.js y **FUNCIONA CORRECTAMENTE** con Google Ads API.
# Force redeploy on Render - Fri Nov 28 13:10:05 -05 2025
