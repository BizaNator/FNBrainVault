from pathlib import Path
import re
import aiohttp
import logging
import os
from urllib.parse import urljoin, urlparse
from typing import Set, Tuple, Optional
from config_manager import ConfigManager
import asyncio

class ImageProcessor:
    def __init__(self, output_dir: str):
        self.config = ConfigManager()
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / 'images'
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.image_refs: Set[Tuple[str, str]] = set()
        self.downloaded_images: Set[str] = set()
        
    class ImageProcessor:
        def __init__(self, output_dir: str):
            self.config = ConfigManager()
            self.output_dir = Path(output_dir)
            self.images_dir = self.output_dir / 'images'
            self.images_dir.mkdir(parents=True, exist_ok=True)
            self.image_refs: Set[Tuple[str, str]] = set()
            self.downloaded_images: Set[str] = set()

            async def process_images(self, content: str, session: aiohttp.ClientSession, base_url: str) -> str:
                """Process all image references and download images"""
                def update_image_path(match) -> str:
                    alt_text = match.group(1) or "Image"
                    img_path = match.group(2)
                    
                    # Handle remote URLs
                    if img_path.startswith(('http://', 'https://')):
                        return self._process_remote_image(match.group(0), img_path, alt_text, session)
                        
                    # Handle relative paths
                    return self._process_relative_image(img_path, alt_text, base_url)
                
                # Process clickable images with remote URLs
                content = re.sub(
                    r'\[!\[(.*?)\]\((.*?)\)\]\((https?://[^)]+)\)',
                    lambda m: m.group(0),  # Keep remote clickable images unchanged
                    content
                )
                
                # Process regular images
                content = re.sub(
                    r'!\[(.*?)\]\(((?:\.\.\/)*(?:images\/)?[^)]+|https?:\/\/[^)]+)\)(?:\{[^}]*\})?',
                    update_image_path,
                    content
                )
                
                return content

            def process_images(self, content: str, file_path: Path) -> str:
                """Synchronous version for offline processing"""
                def update_image_path(match) -> str:
                    alt_text = match.group(1) or "Image"
                    img_path = match.group(2)
                    
                    if 'images' in img_path:
                        img_filename = Path(img_path).name
                        local_ref = f"./images/{img_filename}"
                        self.image_refs.add((img_filename, alt_text))
                        return f"![{alt_text}]({local_ref})"
                    
                    return match.group(0)

                # Process regular images
                content = re.sub(
                    r'!\[(.*?)\]\(((?:\.\.\/)*(?:images\/)?[^)]+)\)(?:\{[^}]*\})?',
                    update_image_path,
                    content
                )
                
                return content
        
    def _process_remote_image(self, original_ref: str, img_url: str, alt_text: str, 
                            session: aiohttp.ClientSession) -> str:
        """Process and download remote images"""
        try:
            img_filename = self._get_image_filename(img_url)
            local_path = self.images_dir / img_filename
            
            if not local_path.exists() and img_url not in self.downloaded_images:
                asyncio.create_task(self._download_image(img_url, local_path, session))
                self.downloaded_images.add(img_url)
            
            self.image_refs.add((img_filename, alt_text))
            return f"![{alt_text}](./images/{img_filename})"
            
        except Exception as e:
            logging.error(f"Error processing remote image {img_url}: {str(e)}")
            return original_ref
            
    def _process_relative_image(self, img_path: str, alt_text: str, base_url: str) -> str:
        """Process relative image paths"""
        if 'images' in img_path:
            img_filename = Path(img_path).name
            local_ref = f"./images/{img_filename}"
            self.image_refs.add((img_filename, alt_text))
            return f"![{alt_text}]({local_ref})"
            
        # Handle other relative paths
        absolute_url = urljoin(base_url, img_path)
        return self._process_remote_image(
            f"![{alt_text}]({img_path})", 
            absolute_url, 
            alt_text
        )
            
    async def _download_image(self, url: str, local_path: Path, 
                            session: aiohttp.ClientSession) -> None:
        """Download image from URL"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    local_path.write_bytes(content)
                    logging.info(f"Downloaded image: {url} -> {local_path}")
                else:
                    logging.error(f"Failed to download image {url}: {response.status}")
        except Exception as e:
            logging.error(f"Error downloading image {url}: {str(e)}")
            
    def _get_image_filename(self, url: str) -> str:
        """Generate consistent filename for image URL"""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"image_{hash(url)}.png"
        return filename
        
    def get_image_references(self) -> Set[Tuple[str, str]]:
        """Return set of processed image references"""
        return self.image_refs 