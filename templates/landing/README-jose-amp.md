# José AMP Template - Documentación

## Descripción
Template AMP de alta conversión para servicios esotéricos y espirituales, optimizado para landing pages de amarres de amor y servicios similares.

## Características Principales
- ✅ AMP válido y optimizado para móviles
- ✅ Diseño responsive con Mystic Dark Luxe theme
- ✅ Integración condicional con Google Tag Manager y StatCounter
- ✅ Soporte completo para user_images del iOS app
- ✅ Fallback automático a URLs por defecto cuando no hay user_images
- ✅ Video principal con poster personalizado
- ✅ Galería de imágenes masonry
- ✅ Testimonios dinámicos
- ✅ WhatsApp integration completa

## Integración con user_images

El template ahora soporta integración completa con el sistema user_images de la app iOS, permitiendo que los usuarios personalicen las imágenes mientras mantienen las URLs originales como fallback.

### Estructura de user_images
```python
user_images = [
    "url_imagen_principal",      # índice 0 - reemplaza main_image
    "url_imagen_experto",       # índice 1 - reemplaza expert_image
    "url_galeria_1",           # índice 2+ - reemplaza gallery_images
    "url_galeria_2",
    "url_galeria_3",
    # ... más imágenes para galería
]
```

### Variables Adicionales para Videos
```python
user_image_main_video = "url_del_video_personalizado"  # reemplaza main_video
user_image_video_poster = "url_del_poster"            # reemplaza video_poster
```

### Comportamiento del Fallback
- Si `user_images` no existe o está vacío → usa URLs por defecto del config
- Si `user_images[0]` existe → usa como imagen principal
- Si `user_images[1]` existe → usa como imagen del experto
- Si `user_images` tiene más de 2 elementos → usa `user_images[2:]` para galería
- Videos usan `user_image_*` si existen, sino URLs por defecto

## Variables de Configuración
Ver `jose-amp-config.json` para todas las variables disponibles y sus valores por defecto.

## Testing
Ejecutar `python3 test_jose_amp.py` para validar el template con datos de ejemplo incluyendo user_images.

## Notas de Implementación
- Mantiene compatibilidad AMP completa
- Todas las imágenes usan lazy loading automático
- Diseño optimizado para conversión en móviles
- Integración perfecta con sistema de keywords dinámicas