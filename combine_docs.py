import os
from pathlib import Path
import yaml
from datetime import datetime
import json
import logging
from typing import Dict, List, Optional, Tuple, Set
from book_formatter import BookFormatter
import re
from doc_types import ChapterInfo
from config_manager import ConfigManager
from markdown_utils import MarkdownProcessor
from image_processor import ImageProcessor

logging.basicConfig(level=logging.INFO)

class DocumentProcessor:
    def __init__(self, docs_dir: str):
        #self.docs_dir = docs_dir
        self.docs_dir = Path(docs_dir)
        self.config = ConfigManager()
        self.formatter = BookFormatter(docs_dir)
        self.markdown_processor = MarkdownProcessor(docs_dir)
        self.image_processor = ImageProcessor(docs_dir)
        self.chapters = {}
        #self.chapters: Dict[int, ChapterInfo] = self.load_chapters()
        self.state = self.load_state()
        self.state_file = Path(docs_dir) / '.doc_state.json'
        self.chapter_file = Path(docs_dir) / '.chapter_index.json'
        self.pages_per_sheet = 2
        self.estimated_lines_per_page = 45
        #self.formatter = BookFormatter(docs_dir)
        #self.image_refs: Set[Tuple[str, str, str]] = set()
        self.internal_links: Dict[str, str] = {}
        
    @property
    def image_refs(self) -> Set[Tuple[str, str]]:
        """Get all processed image references"""
        return self.image_processor.get_image_references()
    
    def load_state(self):
        """Load previous processing state"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            'last_processed': {},
            'last_combined': None,
            'total_pages': 0,
            'chapter_changes': {}  # Track which chapters changed
        }
    
    def load_chapters(self):
        """Load chapter information"""
        if self.chapter_file.exists():
            with open(self.chapter_file, 'r') as f:
                chapter_data = json.load(f)
                return {int(k): ChapterInfo.from_dict(v) for k, v in chapter_data.items()}
        return {}
    
    def save_state(self):
        """Save current processing state"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
            
    def save_chapters(self):
        """Save chapter information"""
        chapter_data = {str(k): v.to_dict() for k, v in self.chapters.items()}
        with open(self.chapter_file, 'w') as f:
            json.dump(chapter_data, f, indent=2)
    
    def estimate_pages(self, content: str) -> int:
        """Estimate number of pages based on content"""
        lines = content.count('\n') + 1
        return (lines // self.estimated_lines_per_page) + 1
    
    def get_chapter_for_file(self, file_path: Path) -> Optional[int]:
        """Determine chapter number from file path or metadata"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.startswith('---'):
                    _, frontmatter, _ = content.split('---', 2)
                    metadata = yaml.safe_load(frontmatter)
                    return metadata.get('chapter')
        except:
            pass
        return None
    
    def generate_print_diff(self, last_version: str, current_version: str) -> List[Tuple[int, int]]:
        """Generate page ranges that need to be printed"""
        changed_pages = []
        for chapter in self.chapters.values():
            if chapter.number in self.state.get('chapter_changes', {}).get(current_version, []):
                changed_pages.append((chapter.start_page, chapter.end_page))
        return changed_pages
    
    def process_content(self, content: str, file_path: Path) -> str:
        """Process and format content before adding to book"""
        # Use formatter for all content processing
        processed_content = self.formatter.process_content(content, file_path)
        
        # Update state tracking
        self.image_refs.update(self.formatter.image_refs)
        self.internal_links.update(self.formatter.internal_links)
        
        return processed_content

    def update_chapter_changes(self, chapter_num: int):
        """Track chapter changes for incremental printing"""
        current_version = datetime.now().isoformat()
        if current_version not in self.state['chapter_changes']:
            self.state['chapter_changes'][current_version] = []
        if chapter_num not in self.state['chapter_changes'][current_version]:
            self.state['chapter_changes'][current_version].append(chapter_num)

    def generate_combined_book(self):
        """Generate combined book with chapter-based organization"""
        output_dir = Path(self.docs_dir) / 'print_ready'
        output_dir.mkdir(exist_ok=True)
        
        # Ensure images directory exists in print_ready
        images_dir = output_dir / 'images'
        images_dir.mkdir(exist_ok=True)
        
        # Copy all images to print_ready/images
        source_images = Path(self.docs_dir) / 'images'
        if source_images.exists():
            import shutil
            for img in source_images.rglob('*'):
                if img.is_file():
                    dest = images_dir / img.name  # Use just the filename
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists():  # Only copy if not already there
                        shutil.copy2(img, dest)
                        logging.info(f"Copied image: {img} -> {dest}")
        
        combined_path = output_dir / 'complete_documentation.md'
        diff_path = output_dir / 'print_updates.md'
        toc_entries = []
        content_blocks = []
        current_page = 1
        
        # Process all markdown files
        for file_path in sorted(Path(self.docs_dir).rglob('*.md')):
            if 'combined' in str(file_path):
                continue
                
            chapter_num = self.get_chapter_for_file(file_path)
            if chapter_num is None:
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract metadata and content
            try:
                if content.startswith('---'):
                    _, frontmatter, content = content.split('---', 2)
                    metadata = yaml.safe_load(frontmatter)
                    title = metadata.get('title', file_path.stem)
                else:
                    title = file_path.stem
            except:
                title = file_path.stem
            
            # Process and format content
            content = self.process_content(content, file_path)
            
            # Create or update chapter info
            if chapter_num not in self.chapters:
                self.chapters[chapter_num] = ChapterInfo(chapter_num, f"Chapter {chapter_num}", current_page)
            
            chapter = self.chapters[chapter_num]
            estimated_pages = self.estimate_pages(content)
            
            # Add to TOC and content with section breaks
            anchor = f"chapter-{chapter_num}"
            toc_entries.append(
                f"- [Chapter {chapter_num}: {chapter.title}](#{anchor}) (Page {chapter.start_page})"
            )
            
            # Add anchors to chapter headers in content
            content_blocks.append(
                f"\n\n{'='*80}\n\n"
                f"# Chapter {chapter_num}: {chapter.title} <a name='{anchor}'></a>\n\n"
                f"{content.strip()}\n\n"
                f"{'='*80}\n"
            )
            
            # Update chapter information
            chapter.end_page = current_page + estimated_pages - 1
            chapter.subsections.append({
                'title': title,
                'start_page': current_page,
                'end_page': current_page + estimated_pages - 1
            })
            
            current_page += estimated_pages
            self.state['last_processed'][str(file_path)] = os.path.getmtime(file_path)
        
        if toc_entries or content_blocks:
            # Generate combined file with enhanced formatting
            with open(combined_path, 'w', encoding='utf-8') as f:
                # Write frontmatter
                f.write("---\n")
                f.write("title: Complete UEFN Documentation\n")
                f.write(f"date: {datetime.now().strftime('%Y-%m-%d')}\n")
                f.write("version: 1.0\n")
                f.write("---\n\n")
                
                # Generate TOC with proper anchors and titles
                toc_entries = ["# Table of Contents\n"]
                for chapter_num, chapter in sorted(self.chapters.items()):
                    anchor = f"chapter-{chapter_num}"
                    title = chapter.title if chapter.title != f"Chapter {chapter_num}" else self.get_chapter_title(chapter_num)
                    toc_entries.append(
                        f"- [Chapter {chapter_num}: {title}](#{anchor}) (Page {chapter.start_page})"
                    )
                    
                    # Add subsection entries if any
                    for section in chapter.subsections:
                        section_anchor = re.sub(r'[^a-z0-9-]', '', section['title'].lower().replace(' ', '-'))
                        toc_entries.append(
                            f"  - [{section['title']}](#{section_anchor}) (Page {section['start_page']})"
                        )
                
                # Add code index after TOC
                if self.formatter.code_blocks:
                    toc_entries.append("\n## Code Examples Index\n")
                    code_index = self.formatter.generate_code_index()
                    toc_entries.extend(code_index.split('\n'))
                
                # Write detailed TOC
                f.write('\n'.join(toc_entries))
                
                # Remove the List of Figures section
                # Just write the content blocks with images
                f.write("\n\n---\n\n")
                f.write('\n'.join(content_blocks))
            
            # Generate print updates guide
            if self.state.get('last_combined'):
                changed_pages = self.generate_print_diff(self.state['last_combined'], 
                                                       datetime.now().isoformat())
                with open(diff_path, 'w', encoding='utf-8') as f:
                    f.write("# Print Updates Guide\n\n")
                    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n")
                    f.write("## Pages to Print\n\n")
                    for start, end in changed_pages:
                        f.write(f"- Pages {start}-{end}\n")
            
            self.state['last_combined'] = datetime.now().isoformat()
            self.state['total_pages'] = current_page - 1
            self.save_state()
            self.save_chapters()
            
            logging.info(f"Generated combined documentation at {combined_path}")
            logging.info(f"Total pages: {self.state['total_pages']}")

    def process_file(self, chapter_number: int, file_path: Path) -> None:
        """
        Process a single documentation file.
        
        Args:
            chapter_number: The chapter number to process
            file_path: Path object pointing to the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process the content using existing methods
            processed_content = self.process_content(content, file_path)
            
            # Update chapter information
            if chapter_number not in self.chapters:
                self.chapters[chapter_number] = ChapterInfo(chapter_number, f"Chapter {chapter_number}", 0)
            
            # Estimate pages and update chapter info
            estimated_pages = self.estimate_pages(processed_content)
            chapter = self.chapters[chapter_number]
            chapter.end_page = chapter.start_page + estimated_pages - 1
            
            # Update state
            self.state['last_processed'][str(file_path)] = os.path.getmtime(file_path)
            self.update_chapter_changes(chapter_number)
            
            logging.info(f"Successfully processed file {file_path.name}")
            
        except Exception as e:
            logging.error(f"Error processing chapter {chapter_number}: {str(e)}")
            raise

    def get_chapter_title(self, chapter_num: int) -> str:
        """Extract meaningful title from chapter content"""
        for file_path in Path(self.docs_dir).rglob('*.md'):
            if chapter_num == self.get_chapter_for_file(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Try to get title from frontmatter
                    if content.startswith('---'):
                        _, frontmatter, _ = content.split('---', 2)
                        metadata = yaml.safe_load(frontmatter)
                        if 'title' in metadata:
                            return metadata['title']
                    # Try to get first header
                    headers = re.findall(r'^#\s+(.+)$', content, flags=re.MULTILINE)
                    if headers:
                        return headers[0]
        return f"Chapter {chapter_num}"

if __name__ == "__main__":
    processor = DocumentProcessor("./downloaded_docs")
    processor.generate_combined_book() 
