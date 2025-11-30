"""
Custom Template Manager
Gestiona templates personalizados creados por usuarios con Grok AI
Guarda en templates/landing/ y templates/previews/ para GitHub Pages
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional

class CustomTemplateManager:
    def __init__(self, 
                 landing_dir: str = "templates/landing",
                 preview_dir: str = "templates/previews",
                 index_dir: str = "custom_templates"):
        """
        Inicializa el gestor de templates personalizados
        
        Args:
            landing_dir: Directorio para templates completos (Jinja2)
            preview_dir: Directorio para previews (HTML renderizado)
            index_dir: Directorio para el índice JSON
        """
        self.landing_dir = landing_dir
        self.preview_dir = preview_dir
        self.index_dir = index_dir
        self.templates_index_file = os.path.join(index_dir, "templates_index.json")
        self._ensure_storage_dirs()
    
    def _ensure_storage_dirs(self):
        """Crea los directorios de almacenamiento si no existen"""
        os.makedirs(self.landing_dir, exist_ok=True)
        os.makedirs(self.preview_dir, exist_ok=True)
        os.makedirs(self.index_dir, exist_ok=True)
        
        # Crear archivo índice si no existe
        if not os.path.exists(self.templates_index_file):
            self._save_index([])
    
    def _load_index(self) -> List[Dict]:
        """Carga el índice de templates"""
        try:
            with open(self.templates_index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading templates index: {e}")
            return []
    
    def _save_index(self, index: List[Dict]):
        """Guarda el índice de templates"""
        with open(self.templates_index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Convierte el nombre del template a un nombre de archivo válido
        Ejemplo: "Template Tarot Místico" -> "template-tarot-mistico"
        """
        # Convertir a minúsculas
        name = name.lower()
        # Reemplazar espacios y caracteres especiales con guiones
        name = re.sub(r'[^a-z0-9]+', '-', name)
        # Eliminar guiones al inicio/final
        name = name.strip('-')
        # Limitar longitud
        return name[:50]
    
    def _generate_preview_html(self, template_content: str, template_data: Dict) -> str:
        """
        Genera un preview HTML renderizando las variables Jinja2 con datos de ejemplo
        
        Args:
            template_content: Contenido HTML/Jinja2 del template
            template_data: Metadata del template para generar valores de ejemplo
            
        Returns:
            HTML con variables reemplazadas
        """
        preview = template_content
        
        # Reemplazar variables comunes de Jinja2 con valores de ejemplo
        replacements = {
            r'\{\{\s*keywords\s*\}\}': ', '.join(template_data.get('keywords', ['servicios', 'profesionales'])),
            r'\{\{\s*business_type\s*\}\}': template_data.get('businessType', 'Servicios Profesionales'),
            r'\{\{\s*target_audience\s*\}\}': template_data.get('targetAudience', 'público general'),
            r'\{\{\s*call_to_action\s*\}\}': template_data.get('callToAction', 'Contactar Ahora'),
            r'\{\{\s*phone\s*\}\}': '+1 (555) 123-4567',
            r'\{\{\s*email\s*\}\}': 'contacto@ejemplo.com',
            r'\{\{\s*whatsapp\s*\}\}': '+1 (555) 123-4567',
            r'\{\{\s*company_name\s*\}\}': template_data.get('businessType', 'Mi Empresa'),
            r'\{\{\s*current_year\s*\}\}': str(datetime.now().year),
        }
        
        for pattern, replacement in replacements.items():
            preview = re.sub(pattern, replacement, preview)
        
        # Eliminar bloques de control Jinja2 que quedan ({% ... %})
        preview = re.sub(r'\{%.*?%\}', '', preview)
        
        # Agregar comentario indicando que es un preview
        preview_header = f"""<!-- 
    PREVIEW GENERADO AUTOMÁTICAMENTE
    Template: {template_data.get('name', 'Sin nombre')}
    Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Nota: Este es un preview estático. El template original usa variables Jinja2.
-->

"""
        return preview_header + preview
    
    def save_template(self, template_data: Dict) -> Dict:
        """
        Guarda un nuevo template personalizado en templates/landing/ y templates/previews/
        
        Args:
            template_data: Diccionario con los datos del template
                - name: Nombre del template
                - content: Código HTML/Jinja2 del template
                - businessType: Tipo de negocio
                - targetAudience: Audiencia objetivo
                - tone: Tono del contenido
                - callToAction: Call to action
                - colorScheme: Esquema de colores
                - sections: Lista de secciones incluidas
                - keywords: Lista de palabras clave
                - campaignId: ID de campaña (opcional)
                - adGroupId: ID de ad group (opcional)
        
        Returns:
            Diccionario con información del template guardado
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Generar nombre de archivo a partir del nombre del template
        base_filename = self._sanitize_filename(template_data.get("name", "template"))
        
        # Verificar si ya existe un template con este nombre
        existing_count = 0
        for template in self._load_index():
            if template.get('baseFilename', '').startswith(base_filename):
                existing_count += 1
        
        # Agregar sufijo si es necesario
        if existing_count > 0:
            filename = f"{base_filename}-{existing_count + 1}.html"
        else:
            filename = f"{base_filename}.html"
        
        preview_filename = filename.replace('.html', '_preview.html')
        
        # Preparar metadata del template
        template_metadata = {
            "name": template_data.get("name"),
            "baseFilename": base_filename,
            "filename": filename,
            "previewFilename": preview_filename,
            "businessType": template_data.get("businessType"),
            "targetAudience": template_data.get("targetAudience"),
            "tone": template_data.get("tone"),
            "callToAction": template_data.get("callToAction"),
            "colorScheme": template_data.get("colorScheme"),
            "sections": template_data.get("sections", []),
            "keywords": template_data.get("keywords", []),
            "campaignId": template_data.get("campaignId"),
            "adGroupId": template_data.get("adGroupId"),
            "createdAt": timestamp,
            "githubLandingPath": f"templates/landing/{filename}",
            "githubPreviewPath": f"templates/previews/{preview_filename}"
        }
        
        content = template_data.get("content", "")
        
        # 1. Guardar template completo (Jinja2) en templates/landing/
        landing_file = os.path.join(self.landing_dir, filename)
        with open(landing_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Template guardado en: {landing_file}")
        
        # 2. Generar y guardar preview en templates/previews/
        preview_content = self._generate_preview_html(content, template_data)
        preview_file = os.path.join(self.preview_dir, preview_filename)
        with open(preview_file, 'w', encoding='utf-8') as f:
            f.write(preview_content)
        print(f"✅ Preview guardado en: {preview_file}")
        
        # 3. Actualizar índice
        index = self._load_index()
        index.append(template_metadata)
        self._save_index(index)
        
        return {
            "success": True,
            "template": template_metadata,
            "message": f"Template '{template_metadata['name']}' guardado exitosamente en templates/landing/ y templates/previews/",
            "files": {
                "landing": landing_file,
                "preview": preview_file
            }
        }
    
    def get_all_templates(self) -> List[Dict]:
        """
        Obtiene la lista de todos los templates personalizados
        
        Returns:
            Lista de metadatos de templates
        """
        return self._load_index()
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict]:
        """
        Obtiene un template por su nombre de archivo
        
        Args:
            template_id: Nombre de archivo del template (puede ser filename o baseFilename)
            
        Returns:
            Diccionario con metadata y contenido del template o None
        """
        index = self._load_index()
        
        for template in index:
            # Buscar por filename exacto o por baseFilename
            if (template.get("filename") == template_id or 
                template.get("baseFilename") == template_id or
                template.get("filename", "").replace('.html', '') == template_id):
                
                # Cargar contenido desde templates/landing/
                template_file = os.path.join(self.landing_dir, template["filename"])
                
                if os.path.exists(template_file):
                    with open(template_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    return {
                        **template,
                        "content": content
                    }
        
        return None
    
    def get_templates_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """
        Busca templates que coincidan con las palabras clave
        
        Args:
            keywords: Lista de palabras clave para buscar
            
        Returns:
            Lista de templates que coinciden
        """
        index = self._load_index()
        matching_templates = []
        
        keywords_lower = [k.lower() for k in keywords]
        
        for template in index:
            template_keywords = [k.lower() for k in template.get("keywords", [])]
            
            # Buscar coincidencias
            matches = set(keywords_lower) & set(template_keywords)
            
            if matches:
                matching_templates.append({
                    **template,
                    "matchCount": len(matches),
                    "matchingKeywords": list(matches)
                })
        
        # Ordenar por número de coincidencias
        matching_templates.sort(key=lambda x: x["matchCount"], reverse=True)
        
        return matching_templates
    
    def delete_template(self, template_id: str) -> Dict:
        """
        Elimina un template de ambas carpetas (landing y preview)
        
        Args:
            template_id: Nombre de archivo del template
            
        Returns:
            Diccionario con resultado de la operación
        """
        index = self._load_index()
        
        template_to_delete = None
        new_index = []
        
        for template in index:
            # Buscar por filename o baseFilename
            if (template.get("filename") == template_id or 
                template.get("baseFilename") == template_id or
                template.get("filename", "").replace('.html', '') == template_id):
                template_to_delete = template
            else:
                new_index.append(template)
        
        if template_to_delete:
            # Eliminar archivo de landing
            landing_file = os.path.join(self.landing_dir, template_to_delete["filename"])
            if os.path.exists(landing_file):
                os.remove(landing_file)
                print(f"✅ Eliminado: {landing_file}")
            
            # Eliminar archivo de preview
            preview_file = os.path.join(self.preview_dir, template_to_delete.get("previewFilename", ""))
            if os.path.exists(preview_file):
                os.remove(preview_file)
                print(f"✅ Eliminado: {preview_file}")
            
            # Actualizar índice
            self._save_index(new_index)
            
            return {
                "success": True,
                "message": f"Template '{template_to_delete['name']}' eliminado exitosamente de landing y preview"
            }
        else:
            return {
                "success": False,
                "message": "Template no encontrado"
            }
    
    def update_template(self, template_id: str, updates: Dict) -> Dict:
        """
        Actualiza un template existente en ambas carpetas
        
        Args:
            template_id: Nombre de archivo del template
            updates: Diccionario con campos a actualizar
            
        Returns:
            Diccionario con resultado de la operación
        """
        index = self._load_index()
        template_found = False
        
        for i, template in enumerate(index):
            if (template.get("filename") == template_id or 
                template.get("baseFilename") == template_id or
                template.get("filename", "").replace('.html', '') == template_id):
                
                template_found = True
                
                # Actualizar metadata
                for key, value in updates.items():
                    if key != "content" and key in template:
                        template[key] = value
                
                template["updatedAt"] = datetime.utcnow().isoformat()
                
                # Actualizar contenido si se proporciona
                if "content" in updates:
                    # Actualizar landing
                    landing_file = os.path.join(self.landing_dir, template["filename"])
                    with open(landing_file, 'w', encoding='utf-8') as f:
                        f.write(updates["content"])
                    
                    # Regenerar preview
                    preview_content = self._generate_preview_html(updates["content"], template)
                    preview_file = os.path.join(self.preview_dir, template.get("previewFilename", ""))
                    with open(preview_file, 'w', encoding='utf-8') as f:
                        f.write(preview_content)
                
                index[i] = template
                break
        
        if template_found:
            self._save_index(index)
            return {
                "success": True,
                "message": "Template actualizado exitosamente en landing y preview"
            }
        else:
            return {
                "success": False,
                "message": "Template no encontrado"
            }
