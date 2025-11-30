#!/usr/bin/env python3
"""
GitHub Integration for Web Cloner
Handles uploading cloned websites to GitHub and optimizing for jsDelivr CDN
"""

import os
import base64
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import time

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class GitHubClonerUploader:
    """Uploads cloned websites to GitHub with jsDelivr optimization"""
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        github_owner: Optional[str] = None,
        github_repo: Optional[str] = None
    ):
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github_owner = github_owner or os.getenv("GITHUB_REPO_OWNER")
        self.github_repo = github_repo or os.getenv("GITHUB_CLONED_REPO", "cloned-websites")
        
        if not self.github_token:
            raise ValueError("GitHub token is required (GITHUB_TOKEN env var)")
        if not self.github_owner:
            raise ValueError("GitHub owner is required (GITHUB_REPO_OWNER env var)")
            
        self.base_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}"
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        self.jsdelivr_base = f"https://cdn.jsdelivr.net/gh/{self.github_owner}/{self.github_repo}@main"
        
        logger.info(f"GitHub uploader initialized for {self.github_owner}/{self.github_repo}")
        
    def ensure_repository_exists(self) -> bool:
        """Ensure the cloned websites repository exists, create if not"""
        try:
            # Check if repo exists
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Repository exists: {self.github_owner}/{self.github_repo}")
                return True
            elif response.status_code == 404:
                # Create repository
                logger.info(f"Creating repository: {self.github_owner}/{self.github_repo}")
                return self._create_repository()
            else:
                logger.error(f"Failed to check repository: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking repository: {str(e)}")
            return False
            
    def _create_repository(self) -> bool:
        """Create the cloned websites repository"""
        try:
            create_url = f"https://api.github.com/user/repos"
            payload = {
                "name": self.github_repo,
                "description": "Cloned websites repository - Automatically generated",
                "private": False,
                "auto_init": True,
                "has_issues": False,
                "has_projects": False,
                "has_wiki": False
            }
            
            response = requests.post(
                create_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 201:
                logger.info(f"✅ Repository created: {self.github_owner}/{self.github_repo}")
                # Wait for initialization
                time.sleep(2)
                return True
            else:
                logger.error(f"Failed to create repository: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating repository: {str(e)}")
            return False
            
    def upload_cloned_website(
        self,
        site_name: str,
        resources: Dict[str, Dict[str, Any]],
        optimize_for_jsdelivr: bool = True
    ) -> Dict[str, Any]:
        """
        Upload a cloned website to GitHub
        
        Args:
            site_name: Unique name for the cloned site
            resources: Dict of {filename: {content, type, url}}
            optimize_for_jsdelivr: Replace local paths with jsDelivr CDN URLs
            
        Returns:
            Dict with upload results and URLs
        """
        logger.info(f"🚀 Uploading cloned website: {site_name}")
        
        # Ensure repository exists
        if not self.ensure_repository_exists():
            return {
                'success': False,
                'error': 'Failed to ensure repository exists'
            }
            
        # Create folder structure
        folder_path = f"clonedwebs/{site_name}"
        
        # Optimize resources for jsDelivr if enabled
        if optimize_for_jsdelivr:
            resources = self._optimize_for_jsdelivr(resources, folder_path)
            
        # Upload each resource
        uploaded_files = []
        failed_files = []
        
        for filename, data in resources.items():
            file_path = f"{folder_path}/{filename}"
            
            try:
                success = self._upload_file(
                    file_path=file_path,
                    content=data['content'],
                    message=f"Add {filename} for {site_name}"
                )
                
                if success:
                    uploaded_files.append(filename)
                    logger.info(f"✅ Uploaded: {filename}")
                else:
                    failed_files.append(filename)
                    logger.warning(f"❌ Failed: {filename}")
                    
            except Exception as e:
                logger.error(f"Error uploading {filename}: {str(e)}")
                failed_files.append(filename)
                
        # Generate URLs
        github_url = f"https://github.com/{self.github_owner}/{self.github_repo}/tree/main/{folder_path}"
        jsdelivr_url = f"{self.jsdelivr_base}/{folder_path}/index.html"
        raw_github_url = f"https://raw.githubusercontent.com/{self.github_owner}/{self.github_repo}/main/{folder_path}/index.html"
        
        result = {
            'success': len(uploaded_files) > 0,
            'site_name': site_name,
            'uploaded_files': len(uploaded_files),
            'failed_files': len(failed_files),
            'total_files': len(resources),
            'github_url': github_url,
            'jsdelivr_url': jsdelivr_url,
            'raw_url': raw_github_url,
            'folder_path': folder_path,
            'files': uploaded_files
        }
        
        if failed_files:
            result['errors'] = failed_files
            
        logger.info(f"✅ Upload complete: {len(uploaded_files)}/{len(resources)} files")
        
        return result
        
    def _upload_file(
        self,
        file_path: str,
        content: bytes,
        message: str,
        branch: str = "main"
    ) -> bool:
        """Upload a single file to GitHub"""
        try:
            # Check if file exists
            check_url = f"{self.base_url}/contents/{file_path}"
            response = requests.get(check_url, headers=self.headers, timeout=10)
            
            sha = None
            if response.status_code == 200:
                sha = response.json().get('sha')
                logger.debug(f"File exists, will update: {file_path}")
                
            # Encode content
            if isinstance(content, str):
                content = content.encode('utf-8')
            content_b64 = base64.b64encode(content).decode('ascii')
            
            # Prepare payload
            payload = {
                "message": message,
                "content": content_b64,
                "branch": branch
            }
            
            if sha:
                payload["sha"] = sha
                
            # Upload
            response = requests.put(
                check_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                return True
            else:
                logger.error(f"Upload failed: {response.status_code} - {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return False
            
    def _optimize_for_jsdelivr(
        self,
        resources: Dict[str, Dict[str, Any]],
        folder_path: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Optimize resources to use jsDelivr CDN URLs
        Replaces local paths with CDN URLs in HTML and CSS
        """
        logger.info("🔧 Optimizing resources for jsDelivr CDN...")
        
        optimized = {}
        cdn_base = f"{self.jsdelivr_base}/{folder_path}"
        
        # Build resource map (filename -> CDN URL)
        resource_map = {}
        for filename in resources.keys():
            if filename != 'index.html':
                cdn_url = f"{cdn_base}/{filename}"
                resource_map[filename] = cdn_url
                
        # Process HTML
        if 'index.html' in resources:
            html_content = resources['index.html']['content']
            if isinstance(html_content, bytes):
                html_content = html_content.decode('utf-8', errors='ignore')
                
            # Replace local references with CDN URLs
            for filename, cdn_url in resource_map.items():
                # Replace various patterns
                patterns = [
                    f'src="{filename}"',
                    f"src='{filename}'",
                    f'href="{filename}"',
                    f"href='{filename}'",
                    f'url({filename})',
                    f'url("{filename}")',
                    f"url('{filename}')",
                ]
                
                for pattern in patterns:
                    replacement = pattern.replace(filename, cdn_url)
                    html_content = html_content.replace(pattern, replacement)
                    
            optimized['index.html'] = {
                'content': html_content.encode('utf-8'),
                'type': resources['index.html']['type'],
                'url': resources['index.html'].get('url', '')
            }
            
        # Process CSS files
        for filename, data in resources.items():
            if filename.endswith('.css'):
                css_content = data['content']
                if isinstance(css_content, bytes):
                    css_content = css_content.decode('utf-8', errors='ignore')
                    
                # Replace url() references
                for other_filename, cdn_url in resource_map.items():
                    if other_filename != filename:
                        patterns = [
                            f'url({other_filename})',
                            f'url("{other_filename}")',
                            f"url('{other_filename}')",
                            f'url(../{other_filename})',
                            f'url("../{other_filename}")',
                            f"url('../{other_filename}')",
                        ]
                        
                        for pattern in patterns:
                            replacement = f'url({cdn_url})'
                            css_content = css_content.replace(pattern, replacement)
                            
                optimized[filename] = {
                    'content': css_content.encode('utf-8'),
                    'type': data['type'],
                    'url': data.get('url', '')
                }
                
        # Copy other resources as-is
        for filename, data in resources.items():
            if filename not in optimized:
                optimized[filename] = data
                
        logger.info(f"✅ Optimized {len(optimized)} resources for jsDelivr")
        
        return optimized
        
    def list_cloned_sites(self) -> List[Dict[str, str]]:
        """List all cloned websites in the repository"""
        try:
            url = f"{self.base_url}/contents/clonedwebs"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                contents = response.json()
                sites = []
                
                for item in contents:
                    if item['type'] == 'dir':
                        site_name = item['name']
                        sites.append({
                            'name': site_name,
                            'github_url': item['html_url'],
                            'jsdelivr_url': f"{self.jsdelivr_base}/clonedwebs/{site_name}/index.html",
                            'path': f"clonedwebs/{site_name}"
                        })
                        
                return sites
            else:
                logger.warning(f"Failed to list sites: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing sites: {str(e)}")
            return []
            
    def delete_cloned_site(self, site_name: str) -> bool:
        """Delete a cloned website (recursively delete folder)"""
        try:
            folder_path = f"clonedwebs/{site_name}"
            
            # Get all files in folder
            url = f"{self.base_url}/contents/{folder_path}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to get folder contents: {response.status_code}")
                return False
                
            files = response.json()
            
            # Delete each file
            for file_data in files:
                if file_data['type'] == 'file':
                    delete_url = f"{self.base_url}/contents/{file_data['path']}"
                    payload = {
                        "message": f"Delete {file_data['name']}",
                        "sha": file_data['sha'],
                        "branch": "main"
                    }
                    
                    del_response = requests.delete(
                        delete_url,
                        headers=self.headers,
                        json=payload,
                        timeout=10
                    )
                    
                    if del_response.status_code not in [200, 204]:
                        logger.warning(f"Failed to delete {file_data['name']}")
                        
            logger.info(f"✅ Deleted cloned site: {site_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting site: {str(e)}")
            return False


def upload_cloned_website(
    site_name: str,
    resources: Dict[str, Dict[str, Any]],
    github_token: Optional[str] = None,
    github_owner: Optional[str] = None,
    optimize_for_jsdelivr: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to upload a cloned website
    
    Usage:
        result = upload_cloned_website(
            site_name='tarot-example',
            resources=cloner.get_resources(),
            optimize_for_jsdelivr=True
        )
    """
    uploader = GitHubClonerUploader(github_token, github_owner)
    return uploader.upload_cloned_website(site_name, resources, optimize_for_jsdelivr)


if __name__ == "__main__":
    # Test GitHub integration
    import sys
    
    uploader = GitHubClonerUploader()
    
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        sites = uploader.list_cloned_sites()
        print("\n🌐 Cloned Websites:")
        print("="*50)
        for site in sites:
            print(f"\n📄 {site['name']}")
            print(f"   GitHub: {site['github_url']}")
            print(f"   jsDelivr: {site['jsdelivr_url']}")
        print("="*50)
    else:
        # Test repository check
        exists = uploader.ensure_repository_exists()
        print(f"\nRepository exists: {exists}")
        
        if exists:
            sites = uploader.list_cloned_sites()
            print(f"Found {len(sites)} cloned websites")
