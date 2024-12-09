import os
from pathlib import Path
import re
import yaml
import logging
from typing import Dict, List, Set, TYPE_CHECKING, Tuple
from datetime import datetime

from image_processor import ImageProcessor

if TYPE_CHECKING:
    from combine_docs import DocumentProcessor

from doc_types import ChapterInfo
from config_manager import ConfigManager

class BookFormatter:
    def __init__(self, docs_dir: str):
        self.docs_dir = Path(docs_dir)
        self.config = ConfigManager()
        self.image_processor = ImageProcessor(docs_dir)
        self.internal_links: Dict[str, str] = {}
        self.code_blocks: List[Dict] = []
        
    def process_content(self, content: str, file_path: Path) -> str:
        """Process and format all content"""
        # Process images using ImageProcessor
        content = self.image_processor.process_images(content, file_path)
        
        # Format code blocks
        content = self.format_code_blocks(content)
        
        # Process internal links
        content = self.process_internal_links(content)
        
        # Create cross-references
        content = self.create_cross_references(content)
        
        return content
        
    @property
    def image_refs(self) -> Set[Tuple[str, str]]:
        """Get all processed image references"""
        return self.image_processor.get_image_references()




    def process_internal_links(self, content: str) -> str:
        """Process internal document links"""
        def is_image_link(text: str) -> bool:
            return (
                text.startswith('![') or 
                any(ext in text.lower() for ext in ['.png', '.jpg', '.gif']) or
                '/images/' in text or
                'cloudfront.net' in text
            )

        def update_link(match):
            link_text = match.group(1)
            link_url = match.group(2)
            
            if is_image_link(link_text) or is_image_link(link_url):
                return match.group(0)
                
            if link_url.startswith(('http://', 'https://', 'mailto:')):
                return match.group(0)
                
            anchor = re.sub(r'[^a-z0-9-]', '', link_text.lower().replace(' ', '-'))
            self.internal_links[link_url] = f"#{anchor}"
            
            return f"[{link_text}](#{anchor})"
            
        return re.sub(r'\[(.*?)\]\((.*?)\)', update_link, content)

    def format_code_blocks(self, content: str) -> str:
        """Format and number code blocks consistently"""
        code_pattern = r'```(\w+)?(?::([^}]+))?\n(.*?)```'
        code_count = 1
        
        def replace_code(match):
            nonlocal code_count
            lang = match.group(1) or 'verse'
            file_path = match.group(2) or ''
            code = match.group(3).strip()
            
            # Create block ID and anchor
            block_id = f"code-block-{code_count}"
            
            # Store code block info
            self.code_blocks.append({
                'id': code_count,
                'language': 'verse',
                'file_path': file_path,
                'preview': code.split('\n')[0][:50].strip(),
                'chapter': getattr(self, 'current_chapter', 0),
                'anchor': block_id
            })
            
            # Format with proper closure and anchor
            formatted = (
                f'<a name="{block_id}"></a>\n'
                f'```verse{":"+file_path if file_path else ""}\n'
                f'{code}\n'
                f'```\n'
            )
            
            code_count += 1
            return formatted
        
        return re.sub(code_pattern, replace_code, content, flags=re.DOTALL)

    def create_cross_references(self, content: str) -> str:
        """Add cross-references between chapters and code blocks"""
        def is_image_link(text: str) -> bool:
            # Check for image file extensions or image paths
            image_patterns = [
                r'\.(?:png|jpg|gif)$',
                r'/images/',
                r'^\.\./\.\./\.\./images/',
                r'^\.\/images\/',
                r'cloudfront\.net.*?/images/'
            ]
            return any(re.search(pattern, text, re.IGNORECASE) for pattern in image_patterns)
        
        # Add chapter references, but skip image links
        def replace_chapter_ref(match):
            chapter = match.group(1)
            full_match = match.group(0)
            
            # Check if this reference is within an image markdown
            pre_context = content[max(0, match.start() - 50):match.start()]
            if '![' in pre_context or is_image_link(pre_context):
                return full_match
            
            return f'[Chapter {chapter}](#chapter-{chapter})'
        
        content = re.sub(r'Chapter (\d+)(?!\])', replace_chapter_ref, content)
        
        # Add code block references, but skip image links
        for block in self.code_blocks:
            ref_pattern = f'Code Block {block["id"]}'
            ref_link = f'[{ref_pattern}](#code-block-{block["id"]})'
            
            # Only replace if not in an image context
            content = re.sub(
                f'(?<!\\!\\[)(?<!\\]\\()({ref_pattern})',
                ref_link,
                content
            )
        
        return content

    def add_section_breaks(self, content: str) -> str:
        """Add clear section breaks between major topics"""
        section_pattern = r'^#\s+(.+)$'
        
        def add_break(match):
            return f'\n{"="*80}\n\n# {match.group(1)}\n'
            
        return re.sub(section_pattern, add_break, content, flags=re.MULTILINE)

    def generate_toc(self, content: str) -> str:
        """Generate detailed table of contents with page numbers"""
        toc = ["# Table of Contents\n"]
        
        def is_image_header(line: str) -> bool:
            # Check if this header is actually an image reference
            return '![' in line or '](' in line or '/images/' in line
        
        # Find all headers but skip image references
        headers = re.finditer(r'^(#+)\s+(.+)$', content, re.MULTILINE)
        
        for match in headers:
            level, title = match.group(1), match.group(2)
            if not is_image_header(title):
                depth = len(level) - 1
                indent = "  " * depth
                clean_title = title.strip()
                anchor = clean_title.lower().replace(' ', '-')
                toc.append(f"{indent}- [{clean_title}](#{anchor})")
        
        return '\n'.join(toc)

    def process_book(self, processor: 'DocumentProcessor') -> str:
        """Process and format the complete book"""
        combined_content = []
        
        # Add book header
        combined_content.append("---")
        combined_content.append("title: UEFN Complete Documentation")
        combined_content.append("version: 1.0")
        combined_content.append("---\n")
        
        # Process each chapter
        for chapter_num in sorted(processor.chapters.keys()):
            chapter = processor.chapters[chapter_num]
            chapter_content = self.process_chapter(chapter)
            combined_content.append(chapter_content)
            
        # Combine all content
        full_content = '\n\n'.join(combined_content)
        
        # Add formatting
        full_content = self.format_code_blocks(full_content)
        full_content = self.create_cross_references(full_content)
        full_content = self.add_section_breaks(full_content)
        
        # Add TOC at the beginning
        toc = self.generate_toc(full_content)
        full_content = f"{toc}\n\n{'='*80}\n\n{full_content}"
        
        return full_content

    def process_chapter(self, chapter: ChapterInfo) -> str:
        """Process individual chapter content"""
        chapter_content = []
        
        # Add chapter header
        chapter_content.append(f"# Chapter {chapter.number}: {chapter.title}\n")
        
        # Process each subsection
        for section in chapter.subsections:
            file_path = self.find_section_file(section['title'])
            if file_path:
                content = self.process_section_content(file_path)
                chapter_content.append(content)
                
        return '\n\n'.join(chapter_content)

    def find_section_file(self, title: str) -> Path:
        """Find markdown file for given section title"""
        for file_path in self.docs_dir.rglob('*.md'):
            if title.lower() in file_path.stem.lower():
                return file_path
        return None

    def process_section_content(self, file_path: Path) -> str:
        """Process individual section content"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Remove frontmatter
        if content.startswith('---'):
            _, _, content = content.split('---', 2)
            
        return content.strip()

    def generate_code_index(self) -> str:
        """Generate indexed list of all code blocks with proper references"""
        if not self.code_blocks:
            return ""
        
        index = []
        
        # Group by chapter
        by_chapter = {}
        for block in self.code_blocks:
            chapter = block['chapter']
            if chapter not in by_chapter:
                by_chapter[chapter] = []
            by_chapter[chapter].append(block)
        
        # Generate organized index
        for chapter in sorted(by_chapter.keys()):
            index.append(f"\n### Chapter {chapter} Code Examples\n")
            for block in by_chapter[chapter]:
                block_title = block['file_path'] if block['file_path'] else f"Code Block {block['id']}"
                entry = f"- [{block_title}](#{block['anchor']})"
                if block['preview']:
                    entry += f": {block['preview']}"
                index.append(entry)
        
        return "\n".join(index)

    def format_documentation(self) -> str:
        """Format entire documentation set"""
        # Create print_ready directory
        print_ready_dir = self.docs_dir / 'print_ready'
        print_ready_dir.mkdir(parents=True, exist_ok=True)
        
        # Process all content
        formatted_content = self.process_book()
        
        # Generate code index
        code_index = self.generate_code_index()
        if code_index:
            formatted_content += f"\n\n# Code Index\n\n{code_index}"
        
        # Save formatted content
        output_path = print_ready_dir / 'complete_documentation.md'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("---\n")
            f.write("title: Complete Documentation\n")
            f.write(f"date: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write("version: 1.0\n")
            f.write("---\n\n")
            f.write(formatted_content)
            
        logging.info(f"Generated formatted documentation at {output_path}")
        return formatted_content

def format_documentation():
    """Main function to format documentation"""
    # Import here to avoid circular import
    from combine_docs import DocumentProcessor
    
    docs_dir = "./downloaded_docs"
    
    # Create print_ready directory if it doesn't exist
    print_ready_dir = Path(docs_dir) / 'print_ready'
    print_ready_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize processor and formatter
    processor = DocumentProcessor(docs_dir)
    
    # Generate formatted book
    formatted_content = processor.generate_combined_book()
    
    # Save formatted book
    output_path = print_ready_dir / 'complete_documentation.md'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Add frontmatter
        f.write("---\n")
        f.write("title: Complete UEFN Documentation\n")
        f.write(f"date: {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write("version: 1.0\n")
        f.write("---\n\n")
        f.write(formatted_content)
        
    logging.info(f"Generated formatted documentation at {output_path}")

if __name__ == "__main__":
    format_documentation() 