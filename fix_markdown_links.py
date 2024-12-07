import os
import logging
from pathlib import Path

import yaml
from markdown_utils import MarkdownProcessor

logging.basicConfig(level=logging.INFO)

def fix_markdown_links(directory: str):
    """Fix markdown links and add chapter numbers in existing files"""
    processor = MarkdownProcessor(directory)
    
    # First pass: collect existing chapter numbers
    for filepath in Path(directory).rglob('*.md'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                metadata, _ = processor.fix_frontmatter(content)
                if chapter := metadata.get('chapter'):
                    try:
                        processor.existing_chapters[str(filepath)] = int(chapter)
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            logging.warning(f"Error reading {filepath}: {e}")

    # Second pass: fix links and add missing chapter numbers
    for filepath in Path(directory).rglob('*.md'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Fix frontmatter and content structure
            content, content_modified = processor.fix_frontmatter_and_content(content, filepath)
            modified = content_modified
            
            metadata, rest = processor.fix_frontmatter(content)
            
            # Add or update chapter number
            chapter_num = processor.generate_chapter_number(filepath)
            metadata['chapter'] = chapter_num
            processor.existing_chapters[str(filepath)] = chapter_num
            
            # Reconstruct content with fixed frontmatter
            if modified or 'chapter' not in metadata:
                content = f"---\n{yaml.dump(metadata, allow_unicode=True, default_flow_style=False)}---\n\n{rest}"
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                logging.info(f"Updated {filepath}")
            
        except Exception as e:
            logging.error(f"Error processing {filepath}: {str(e)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "./downloaded_docs"
    fix_markdown_links(directory) 