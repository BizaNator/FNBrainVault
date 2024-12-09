import os
import re
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urljoin, urlparse
from config_manager import ConfigManager
from image_processor import ImageProcessor

class MarkdownProcessor:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.config = ConfigManager()
        self.image_processor = ImageProcessor(output_dir)
        self.existing_chapters = {}
        self.processed_urls = set()
        #self.image_refs = set()

    def clean_title(self, title: str) -> str:
        """Clean up title by removing common documentation suffixes."""
        patterns = [
            r'\s*-\s*Unreal Editor for Fortnite Documentation.*$',
            r'\s*-\s*Epic Games.*$',
            r'\s*-\s*Documentation.*$',
            r'\s*-\s*Epic Developer.*$',
            r'\s*-\s*Unreal Editor for Fortnite.*$',
            r'\s*-\s*UEFN.*$',
            r'\s*\|.*$',
            r'\s+$'
        ]
        
        for pattern in patterns:
            title = re.sub(pattern, '', title)
        
        return title.strip()

    def fix_frontmatter(self, content: str) -> tuple[dict, str]:
        """Fix and parse frontmatter, returning (metadata, rest_of_content)"""
        if not content.startswith('---'):
            return {}, content
            
        try:
            parts = content.split('---', 2)
            if len(parts) < 3:
                return {}, content
                
            frontmatter, rest = parts[1], parts[2]
            
            # Clean up problematic characters
            frontmatter = frontmatter.replace('|', '-')
            frontmatter = re.sub(r':\s+', ': ', frontmatter)
            frontmatter = re.sub(r'[^\x00-\x7F]+', '', frontmatter)
            
            try:
                metadata = yaml.safe_load(frontmatter) or {}
            except yaml.YAMLError:
                metadata = {}
                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
            
            return metadata, rest
            
        except Exception as e:
            logging.debug(f"Error processing frontmatter: {str(e)}")
            return {}, content

    def fix_frontmatter_and_content(self, content: str, filepath: Path) -> tuple[str, bool]:
        """Fix frontmatter and content structure"""
        metadata, rest = self.fix_frontmatter(content)
        modified = False
        
        is_glossary = 'glossary' in str(filepath).lower()
        
        # Clean up title
        if 'title' in metadata:
            cleaned_title = self.clean_title(metadata['title'])
            if is_glossary and not cleaned_title.startswith('Glossary'):
                cleaned_title = f"Glossary - {cleaned_title}"
            if cleaned_title != metadata['title']:
                metadata['title'] = cleaned_title
                modified = True
        else:
            base_title = self.clean_title(filepath.stem.replace('_', ' ').title())
            if is_glossary:
                base_title = f"Glossary - {base_title}"
            metadata['title'] = base_title
            modified = True
        
        # Fix content title
        first_line_pattern = r'^# .*$'
        if match := re.search(first_line_pattern, rest.lstrip(), re.MULTILINE):
            original_title = match.group(0)
            new_title = f"# {metadata['title']}"
            if original_title != new_title:
                rest = rest.replace(original_title, new_title, 1)
                modified = True
        
        # Extract description if missing
        if 'description' not in metadata:
            first_para = re.search(r'\n\n([^#\n][^\n]+)', rest)
            if first_para:
                metadata['description'] = first_para.group(1).strip()
                modified = True
        
        # Ensure proper content structure
        title_pattern = f"# {re.escape(metadata['title'])}"
        rest = rest.strip()
        has_title = bool(re.match(title_pattern, rest))
        has_description = False
        
        if 'description' in metadata:
            desc_pattern = f"\n\n{re.escape(metadata['description'])}\n"
            has_description = bool(re.search(desc_pattern, rest))
        
        if not (has_title and has_description):
            new_content = []
            if not has_title:
                new_content.append(f"# {metadata['title']}")
            else:
                first_line = rest.split('\n')[0]
                new_content.append(first_line)
                rest = '\n'.join(rest.split('\n')[1:])
            
            if 'description' in metadata and not has_description:
                new_content.append("")
                new_content.append(metadata['description'])
            
            new_content.append("")
            new_content.append(rest.lstrip('# \n'))
            
            rest = '\n'.join(new_content)
            modified = True
        
        # Remove duplicate titles
        lines = rest.strip().split('\n')
        if len(lines) >= 2 and lines[0].startswith('# ') and lines[1].startswith('# '):
            rest = '\n'.join([lines[0]] + lines[2:])
            modified = True
        
        if modified:
            content = f"---\n{yaml.dump(metadata, allow_unicode=True, default_flow_style=False)}---\n\n{rest}"
        
        return content, modified

    def generate_chapter_number(self, filepath: Path) -> int:
        """Generate a chapter number based on file path and content"""
        path_str = str(filepath)
        
        # API group check
        api_match = re.search(r'verse-api/.*?/devices/(\w+)/', path_str)
        if api_match:
            device_name = api_match.group(1)
            for existing_path, chapter in self.existing_chapters.items():
                if device_name in existing_path:
                    return chapter
            return 1000 + len({p for p in self.existing_chapters.keys() if 'verse-api' in p})

        # Template series check
        template_match = re.search(r'([\w-]+)-\d+', filepath.stem)
        if template_match:
            base_name = template_match.group(1)
            for existing_path, chapter in self.existing_chapters.items():
                if base_name in Path(existing_path).stem:
                    return chapter
            return 500 + len({p for p in self.existing_chapters.keys() if base_name in Path(p).stem})

        # Feature groups check
        feature_match = re.search(r'using-([a-z-]+)-.*?-in-', path_str)
        if feature_match:
            feature_name = feature_match.group(1)
            for existing_path, chapter in self.existing_chapters.items():
                if feature_name in existing_path:
                    return chapter
            return 100 + len({p for p in self.existing_chapters.keys() if 'using-' in p})

        # Priority patterns
        patterns = [
            (r'chapter[_-]?(\d+)', 100),
            (r'ch[_-]?(\d+)', 100),
            (r'/(\d+)[_-]', 100),
            (r'getting[_-]started', 1),
            (r'introduction', 2),
            (r'overview', 3),
            (r'basic', 10),
            (r'advanced', 50),
            (r'reference', 80),
            (r'api', 90)
        ]
        
        for pattern, base_num in patterns:
            if match := re.search(pattern, path_str, re.IGNORECASE):
                if group := match.group(1):
                    return int(group)
                return base_num
                
        return max(self.existing_chapters.values(), default=0) + 1

    async def process_images(self, content: str, session, base_url: str) -> str:
        #"""Process images in content, downloading them and updating links"""
        """Process all images in content"""
        return await self.image_processor.process_images(content, session, base_url)

        #image_pattern = r'!\[(.*?)\]\((.*?)\)'
        #images = re.findall(image_pattern, content)
        
        #for alt_text, image_url in images:
        #    image_path = await self.download_image(session, image_url, base_url)
        #    if image_path:
        #        relative_path = '../../../images/' + os.path.basename(image_path)
        #        relative_path = relative_path.replace('\\', '/')
                
        #        content = content.replace(
        #            f'![{alt_text}]({image_url})',
        #            f'![{alt_text}]({relative_path})'
        #            )
        #        self.image_refs.add(relative_path)
        
        #return content

    async def download_image(self, session, img_url: str, base_url: str) -> Optional[str]:
        """Download and optimize an image"""
        try:
            parsed_url = urlparse(img_url)
            original_filename = os.path.basename(parsed_url.path)
            clean_filename = re.sub(r'[^\w\-.]', '_', original_filename)
            
            image_dir = os.path.join(self.output_dir, 'images')
            image_path = os.path.join(image_dir, clean_filename)
            
            base, ext = os.path.splitext(image_path)
            counter = 1
            while os.path.exists(image_path):
                image_path = f"{base}_{counter}{ext}"
                counter += 1
            
            os.makedirs(image_dir, exist_ok=True)

            if not os.path.exists(image_path):
                full_url = img_url if bool(parsed_url.netloc) else urljoin(base_url, img_url)
                
                async with session.get(full_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(image_path, 'wb') as f:
                            f.write(content)
                        return image_path
                    else:
                        logging.error(f"Failed to download image {img_url}: {response.status}")
                        return None
            return image_path
        except Exception as e:
            logging.error(f"Error downloading image {img_url}: {str(e)}")
            return None

    async def process_internal_links(self, content: str, base_url: str, current_file_path: str) -> str:
        """Update internal documentation links"""
        link_pattern = r'(?<!!)\[(.*?)\]\((.*?)(?:#(.*?))?\)'
        links = re.findall(link_pattern, content)
        
        for link_text, link_url, anchor in links:
            if '/documentation/en-us/' in link_url or not link_url.startswith(('http://', 'https://', '/')):
                local_filename = link_url.rstrip('/').split('/')[-1]
                local_filename = "".join(x for x in local_filename if x.isalnum() or x in [' ', '-', '_'])
                local_filename = local_filename.replace(' ', '_')
                
                if not local_filename.endswith('.md'):
                    local_filename += '.md'
                
                current_file = os.path.basename(current_file_path)
                
                if local_filename == current_file or (
                    'glossary' in current_file and local_filename.startswith('verse-glossary')
                ):
                    if anchor:
                        new_link = f'[{link_text}](#{anchor})'
                    else:
                        term = local_filename.replace('verse-glossary', '').replace('.md', '').lower()
                        if term:
                            new_link = f'[{link_text}](#{term})'
                        else:
                            continue
                    
                    content = content.replace(
                        f'[{link_text}]({link_url}{"#"+anchor if anchor else ""})',
                        new_link
                    )
                    continue
                
                doc_root = Path(self.output_dir)
                current_dir = Path(current_file_path).parent
                target_files = list(doc_root.rglob(local_filename))
                
                if target_files:
                    target_path = target_files[0]
                    relative_path = os.path.relpath(target_path, current_dir)
                    relative_path = relative_path.replace('\\', '/')
                    
                    if anchor:
                        relative_path = f"{relative_path}#{anchor}"
                    
                    content = content.replace(
                        f'[{link_text}]({link_url}{"#"+anchor if anchor else ""})',
                        f'[{link_text}]({relative_path})'
                    )
        
        return content

    def save_content(self, url: str, content: str, title: str) -> str:
        """Save processed content to file"""
        parsed_url = urlparse(url)
        relative_path = parsed_url.path.lstrip('/')
        filepath = os.path.join(self.output_dir, relative_path)
        
        if not filepath.endswith('.md'):
            filepath += '.md'
            
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        metadata = {
            "title": title.strip(),
            "tags": ["UEFN", "Epic Games", "Documentation"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source_url": url,
            "author": "Epic Games"
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('---\n')
            for key, value in metadata.items():
                if isinstance(value, list):
                    f.write(f'{key}:\n')
                    for item in value:
                        f.write(f'  - {item}\n')
                else:
                    f.write(f'{key}: {value}\n')
            f.write('---\n\n')
            f.write(content)
        
        return filepath 
    
    @property
    def image_refs(self) -> set[Tuple[str, str]]:
        """Get all processed image references"""
        return self.image_processor.get_image_references()

    def process_content(self, content: str, file_path: Path) -> str:
        """Process all markdown content"""
        # Fix frontmatter
        content, _ = self.fix_frontmatter_and_content(content, file_path)
        
        # Process images
        content = self.process_images(content, file_path)
        
        # Process internal links
        content = self.process_internal_links(content, "", str(file_path))
        
        return content