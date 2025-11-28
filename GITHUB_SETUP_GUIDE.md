# 🚀 Guía Completa: Cómo Obtener Tokens de GitHub

## Paso 1: Obtener GITHUB_REPO_OWNER

### Opción A: Si usas tu cuenta personal
- Ve a https://github.com
- El `GITHUB_REPO_OWNER` es tu **nombre de usuario de GitHub**
- Ejemplo: Si tu perfil es `https://github.com/johndoe`, entonces:
  ```bash
  export GITHUB_REPO_OWNER="johndoe"
  ```

### Opción B: Si usas una organización
- El `GITHUB_REPO_OWNER` es el **nombre de la organización**
- Ejemplo: Si la organización es `https://github.com/mi-empresa`, entonces:
  ```bash
  export GITHUB_REPO_OWNER="mi-empresa"
  ```

## Paso 2: Obtener GITHUB_REPO_NAME

### Crear un repositorio para las landing pages
1. Ve a https://github.com y haz clic en **"New repository"**
2. Nombre sugerido: `landing-pages` o `monorepo-landings`
3. **IMPORTANTE**: El repositorio debe ser **PÚBLICO** para que funcione correctamente
4. Haz clic en **"Create repository"**

### Configurar la variable
```bash
export GITHUB_REPO_NAME="landing-pages"
```

## Paso 3: Obtener GITHUB_TOKEN (Personal Access Token)

### Paso a paso para crear el token:

1. **Ve a GitHub Settings**:
   - Ve a https://github.com/settings/tokens
   - O ve a https://github.com/settings/tokens?type=beta (nueva interfaz)

2. **Generar nuevo token**:
   - Haz clic en **"Generate new token"** → **"Generate new token (classic)"**

3. **Configurar el token**:
   - **Token name**: `landing-pages-generator`
   - **Expiration**: Selecciona **"No expiration"** (sin expiración)

4. **Permisos requeridos** (marca estas casillas):
   - ✅ **repo** (Full control of private repositories)
   - ✅ **public_repo** (Access public repositories)
   - ✅ **workflow** (Update GitHub Action workflows)

5. **Crear el token**:
   - Haz clic en **"Generate token"**
   - **IMPORTANTE**: Copia el token inmediatamente (solo se muestra una vez)

### Configurar la variable
```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## Paso 4: Verificar la Configuración

### Ejecutar el diagnóstico:
```bash
python3 github_diagnostics.py
```

Deberías ver algo como:
```
📋 Environment Variables:
✅ GITHUB_REPO_OWNER: johndoe
✅ GITHUB_REPO_NAME: landing-pages
✅ GITHUB_TOKEN: ***xxxx

✅ Repository found: johndoe/landing-pages
✅ All GitHub checks passed!
```

## 🔧 Configuración en Producción (Render.com)

### Para Render.com, agrega estas variables de entorno:

1. Ve a tu dashboard de Render.com
2. Selecciona tu servicio
3. Ve a **Environment**
4. Agrega estas variables:

```
GITHUB_REPO_OWNER = johndoe
GITHUB_REPO_NAME = landing-pages
GITHUB_TOKEN = ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 🧪 Probar que Funciona

### Una vez configurado, prueba el sistema:
```bash
# Ejecutar diagnóstico
python3 github_diagnostics.py

# Si todo está bien, el generador debería funcionar
```

## 🔒 Seguridad del Token

### ⚠️ **IMPORTANTE**:
- **Nunca** compartas tu token en código público
- **Nunca** lo commits en Git
- El token tiene acceso completo a tus repositorios
- Si lo comprometen, revócalo inmediatamente en GitHub Settings

### 💡 **Recomendaciones**:
- Usa tokens con expiración corta en desarrollo
- Crea tokens específicos para cada proyecto
- Revisa regularmente los tokens activos
- Usa GitHub Apps en lugar de tokens personales para producción

## 🚨 Solución de Problemas

### Si el diagnóstico falla:

1. **"Repository not found"**:
   - Verifica que el repositorio existe y es público
   - Confirma que `GITHUB_REPO_OWNER` y `GITHUB_REPO_NAME` son correctos

2. **"No push permissions"**:
   - Asegúrate de que tienes permisos de escritura en el repositorio
   - Para repositorios de organización, pide acceso al admin

3. **"Authentication failed"**:
   - Regenera el token
   - Verifica que el token no haya expirado
   - Confirma que tienes los scopes correctos

## 📞 Soporte

Si sigues teniendo problemas:
1. Ejecuta `python3 github_diagnostics.py`
2. Comparte la salida completa
3. Verifica que seguiste todos los pasos de esta guía</content>
<parameter name="filePath">/Users/edwarbechara/Documents/app-reportes-pagos-BACKUP-20250702-123421/google-ads-backend-python/GITHUB_SETUP_GUIDE.md