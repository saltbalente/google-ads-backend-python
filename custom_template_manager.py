"""
Custom Template Manager
Gestiona templates personalizados creados por usuarios con Grok AI
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional

class CustomTemplateManager:
    def __init__(self, storage_dir: str = "custom_templates"):
        """
        Inicializa el gestor de templates personalizados
        
        Args:
            storage_dir: Directorio donde se guardarán los templates
        """
        self.storage_dir = storage_dir
        self.templates_index_file = os.path.join(storage_dir, "templates_index.json")
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """Crea el directorio de almacenamiento si no existe"""
        os.makedirs(self.storage_dir, exist_ok=True)
        
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
    
    def save_template(self, template_data: Dict) -> Dict:
        """
        Guarda un nuevo template personalizado
        
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
        # Generar ID único
        template_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Preparar metadata del template
        template_metadata = {
            "id": template_id,
            "name": template_data.get("name"),
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
            "filename": f"{template_id}.html"
        }
        
        # Guardar contenido del template
        template_file = os.path.join(self.storage_dir, template_metadata["filename"])
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(template_data.get("content", ""))
        
        # Actualizar índice
        index = self._load_index()
        index.append(template_metadata)
        self._save_index(index)
        
        return {
            "success": True,
            "template": template_metadata,
            "message": f"Template '{template_metadata['name']}' guardado exitosamente"
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
        Obtiene un template por su ID
        
        Args:
            template_id: ID del template
            
        Returns:
            Diccionario con metadata y contenido del template o None
        """
        index = self._load_index()
        
        for template in index:
            if template["id"] == template_id:
                # Cargar contenido
                template_file = os.path.join(self.storage_dir, template["filename"])
                
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
        Elimina un template
        
        Args:
            template_id: ID del template a eliminar
            
        Returns:
            Diccionario con resultado de la operación
        """
        index = self._load_index()
        
        template_to_delete = None
        new_index = []
        
        for template in index:
            if template["id"] == template_id:
                template_to_delete = template
            else:
                new_index.append(template)
        
        if template_to_delete:
            # Eliminar archivo
            template_file = os.path.join(self.storage_dir, template_to_delete["filename"])
            
            if os.path.exists(template_file):
                os.remove(template_file)
            
            # Actualizar índice
            self._save_index(new_index)
            
            return {
                "success": True,
                "message": f"Template '{template_to_delete['name']}' eliminado exitosamente"
            }
        else:
            return {
                "success": False,
                "message": "Template no encontrado"
            }
    
    def update_template(self, template_id: str, updates: Dict) -> Dict:
        """
        Actualiza un template existente
        
        Args:
            template_id: ID del template
            updates: Diccionario con campos a actualizar
            
        Returns:
            Diccionario con resultado de la operación
        """
        index = self._load_index()
        template_found = False
        
        for i, template in enumerate(index):
            if template["id"] == template_id:
                template_found = True
                
                # Actualizar metadata
                for key, value in updates.items():
                    if key != "content" and key in template:
                        template[key] = value
                
                template["updatedAt"] = datetime.utcnow().isoformat()
                
                # Actualizar contenido si se proporciona
                if "content" in updates:
                    template_file = os.path.join(self.storage_dir, template["filename"])
                    with open(template_file, 'w', encoding='utf-8') as f:
                        f.write(updates["content"])
                
                index[i] = template
                break
        
        if template_found:
            self._save_index(index)
            return {
                "success": True,
                "message": "Template actualizado exitosamente"
            }
        else:
            return {
                "success": False,
                "message": "Template no encontrado"
            }
