"""
Video Processor Module
Handles video upload, download, thumbnail generation, and CDN integration
"""

import os
import re
import logging
import base64
import requests
import tempfile
import hashlib
from typing import Dict, Optional, Tuple
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_VIDEO_SIZE_MB = 100  # Maximum video size in MB
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720

class VideoProcessor:
    """Process videos for landing pages with thumbnail generation and CDN upload"""
    
    def __init__(self, github_owner: str, github_repo: str, github_token: str):
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.github_token = github_token
        self.headers = {"Authorization": f"token {github_token}"}
        
    def validate_video_url(self, url: str) -> bool:
        """Validate if URL is accessible and is a video"""
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code != 200:
                return False
                
            content_type = response.headers.get('Content-Type', '').lower()
            return 'video' in content_type or any(fmt in url.lower() for fmt in SUPPORTED_VIDEO_FORMATS)
        except Exception as e:
            logger.error(f"Error validating video URL: {e}")
            return False
    
    def download_video_from_url(self, url: str) -> Optional[bytes]:
        """Download video from external URL"""
        try:
            logger.info(f"Downloading video from: {url}")
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Check file size
            content_length = int(response.headers.get('Content-Length', 0))
            if content_length > MAX_VIDEO_SIZE_MB * 1024 * 1024:
                raise ValueError(f"Video size exceeds {MAX_VIDEO_SIZE_MB}MB limit")
            
            video_data = b''
            for chunk in response.iter_content(chunk_size=8192):
                video_data += chunk
                if len(video_data) > MAX_VIDEO_SIZE_MB * 1024 * 1024:
                    raise ValueError(f"Video size exceeds {MAX_VIDEO_SIZE_MB}MB limit")
            
            logger.info(f"Downloaded video: {len(video_data)} bytes")
            return video_data
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    def generate_thumbnail(self, video_data: bytes, position: str = "hero") -> Optional[bytes]:
        """Generate thumbnail from video using moviepy"""
        try:
            # Try using moviepy first
            try:
                from moviepy.editor import VideoFileClip
                
                # Save video to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                    temp_video.write(video_data)
                    temp_video_path = temp_video.name
                
                # Extract frame at 1 second
                clip = VideoFileClip(temp_video_path)
                duration = clip.duration
                frame_time = min(1.0, duration * 0.1)  # 10% into video or 1 second
                
                frame = clip.get_frame(frame_time)
                clip.close()
                
                # Convert frame to PIL Image
                image = Image.fromarray(frame)
                
                # Clean up temp file
                os.unlink(temp_video_path)
                
            except ImportError:
                # Fallback to opencv if moviepy not available
                import cv2
                import numpy as np
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                    temp_video.write(video_data)
                    temp_video_path = temp_video.name
                
                # Open video
                cap = cv2.VideoCapture(temp_video_path)
                
                # Get total frames
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                frame_number = min(30, int(total_frames * 0.1))  # 10% into video or frame 30
                
                # Set frame position
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                # Read frame
                ret, frame = cap.read()
                cap.release()
                
                if not ret:
                    raise Exception("Could not read video frame")
                
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb)
                
                # Clean up
                os.unlink(temp_video_path)
            
            # Resize thumbnail maintaining aspect ratio
            image.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
            thumbnail_bytes = img_byte_arr.getvalue()
            
            logger.info(f"Generated thumbnail: {len(thumbnail_bytes)} bytes")
            return thumbnail_bytes
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None
    
    def upload_to_github(self, video_data: bytes, folder_name: str, filename: str) -> str:
        """Upload video to GitHub repository"""
        try:
            # Create safe filename
            safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
            file_path = f"{folder_name}/{safe_filename}"
            
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{file_path}"
            
            # Check if file exists
            existing_response = requests.get(url, headers=self.headers)
            sha = None
            if existing_response.status_code == 200:
                sha = existing_response.json().get('sha')
            
            # Prepare upload data
            data = {
                "message": f"Add video: {safe_filename}",
                "content": base64.b64encode(video_data).decode('utf-8')
            }
            
            if sha:
                data["sha"] = sha
            
            # Upload file
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            # Get download URL
            download_url = response.json()['content']['download_url']
            logger.info(f"Uploaded video to GitHub: {download_url}")
            
            return download_url
            
        except Exception as e:
            logger.error(f"Error uploading video to GitHub: {e}")
            raise
    
    def process_video(self, video_source: str, folder_name: str, position: str, 
                     is_url: bool = False) -> Dict[str, str]:
        """
        Process video from URL or base64 data
        
        Args:
            video_source: URL or base64 encoded video data
            folder_name: Landing folder name
            position: Video position (hero, middle, testimonials)
            is_url: Whether video_source is a URL
            
        Returns:
            Dict with video_url and thumbnail_url
        """
        try:
            # Get video data
            if is_url:
                if not self.validate_video_url(video_source):
                    raise ValueError("Invalid video URL")
                video_data = self.download_video_from_url(video_source)
                if not video_data:
                    raise ValueError("Failed to download video")
            else:
                # Decode base64
                video_data = base64.b64decode(video_source)
            
            # Validate size
            if len(video_data) > MAX_VIDEO_SIZE_MB * 1024 * 1024:
                raise ValueError(f"Video exceeds {MAX_VIDEO_SIZE_MB}MB limit")
            
            # Generate filename hash
            video_hash = hashlib.md5(video_data).hexdigest()[:12]
            video_filename = f"video_{position}_{video_hash}.mp4"
            thumbnail_filename = f"video_{position}_{video_hash}_thumb.jpg"
            
            # Upload video
            video_url = self.upload_to_github(video_data, folder_name, video_filename)
            
            # Generate and upload thumbnail
            thumbnail_data = self.generate_thumbnail(video_data, position)
            thumbnail_url = None
            
            if thumbnail_data:
                thumbnail_url = self.upload_to_github(thumbnail_data, folder_name, thumbnail_filename)
            
            return {
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "position": position,
                "size_bytes": len(video_data)
            }
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            raise
    
    def get_video_info(self, video_data: bytes) -> Dict:
        """Get video metadata (duration, resolution, format)"""
        try:
            try:
                from moviepy.editor import VideoFileClip
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                    temp_video.write(video_data)
                    temp_video_path = temp_video.name
                
                clip = VideoFileClip(temp_video_path)
                
                info = {
                    "duration": clip.duration,
                    "width": clip.w,
                    "height": clip.h,
                    "fps": clip.fps,
                    "orientation": "vertical" if clip.h > clip.w else "horizontal"
                }
                
                clip.close()
                os.unlink(temp_video_path)
                
                return info
                
            except ImportError:
                # Fallback to opencv
                import cv2
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                    temp_video.write(video_data)
                    temp_video_path = temp_video.name
                
                cap = cv2.VideoCapture(temp_video_path)
                
                info = {
                    "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS),
                    "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    "fps": cap.get(cv2.CAP_PROP_FPS),
                    "orientation": "vertical" if cap.get(cv2.CAP_PROP_FRAME_HEIGHT) > cap.get(cv2.CAP_PROP_FRAME_WIDTH) else "horizontal"
                }
                
                cap.release()
                os.unlink(temp_video_path)
                
                return info
                
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}
