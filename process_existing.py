from combine_docs import DocumentProcessor
from book_formatter import BookFormatter
from markdown_utils import MarkdownProcessor
import logging
import sys
import os
from pathlib import Path
import json
import time
import asyncio
import aiohttp
from typing import Optional, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)

if os.name == 'nt':  # Windows
    import msvcrt
else:  # Unix
    import tty
    import termios

def check_for_keypress():
    if os.name == 'nt':
        return msvcrt.kbhit()
    else:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            return ch if ch else None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

class ProcessingManager:
    def __init__(self, docs_dir: str = "./downloaded_docs"):
        self.docs_dir = docs_dir
        self.state_file = Path(docs_dir) / '.processing_state.json'
        self.processor = DocumentProcessor(docs_dir)
        self.markdown_processor = MarkdownProcessor(docs_dir)
        self.paused = False
        self.current_chapter = 0
        self.load_state()

    def load_state(self):
        """Load processing state"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                self.current_chapter = state.get('last_chapter', 0)
        
    def save_state(self):
        """Save current processing state"""
        with open(self.state_file, 'w') as f:
            json.dump({
                'last_chapter': self.current_chapter,
                'timestamp': time.time()
            }, f)

    def show_menu(self) -> tuple[str, Optional[int], Optional[int], bool]:
        """Display interactive menu and get user choice"""
        while True:
            print("\nUEFN Documentation Processor")
            print("=" * 30)
            print("1. Process all chapters (offline)")
            print("2. Process new chapters only (offline)")
            print("3. Process specific chapter range (offline)")
            print("4. Resume from last position (offline)")
            print("5. Update online documentation")
            print("6. Fix markdown links")
            print("7. Generate combined book")
            print("8. Exit")
            
            choice = input("\nEnter your choice (1-8): ")
            
            if choice == '1':
                return 'all', None, None, False
            elif choice == '2':
                return 'new', None, None, False
            elif choice == '3':
                try:
                    start = int(input("Enter start chapter number: "))
                    end = int(input("Enter end chapter number: "))
                    return 'range', start, end, False
                except ValueError:
                    print("Invalid input. Please enter numbers only.")
                    continue
            elif choice == '4':
                return 'resume', None, None, False
            elif choice == '5':
                return 'online', None, None, True
            elif choice == '6':
                return 'fix_links', None, None, False
            elif choice == '7':
                return 'combine', None, None, False
            elif choice == '8':
                sys.exit(0)
            else:
                print("Invalid choice. Please try again.")

    async def process_online_docs(self, base_url: str = "https://dev.epicgames.com/documentation/en-us/uefn"):
        """Process online documentation"""
        try:
            logging.info(f"Processing online documentation from {base_url}")
            
            async with aiohttp.ClientSession() as session:
                # Get initial page
                async with session.get(base_url) as response:
                    if response.status != 200:
                        logging.error(f"Failed to access {base_url}: {response.status}")
                        return
                    
                    content = await response.text()
                    await self.process_page(base_url, content, session)
                    
                # Process any queued pages
                while self.markdown_processor.processed_urls:
                    url = self.markdown_processor.processed_urls.pop()
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            await self.process_page(url, content, session)
                        else:
                            logging.error(f"Failed to access {url}: {response.status}")
            
            logging.info("Online documentation processing complete!")
            
        except Exception as e:
            logging.error(f"Error processing online documentation: {str(e)}")
            self.save_state()

    async def process_page(self, url: str, content: str, session):
        """Process a single documentation page"""
        try:
            # Convert HTML to markdown
            markdown_content = self.markdown_processor.html_to_markdown(content)
            
            # Process images and links
            markdown_content = await self.markdown_processor.process_images(markdown_content, session, url)
            markdown_content = await self.markdown_processor.process_internal_links(markdown_content, url, url)
            
            # Save processed content
            title = self.markdown_processor.extract_title(content) or os.path.basename(url)
            filepath = self.markdown_processor.save_content(url, markdown_content, title)
            
            logging.info(f"Processed {url} -> {filepath}")
            
        except Exception as e:
            logging.error(f"Error processing page {url}: {str(e)}")

    def process_docs(self, mode: str, start_chapter: Optional[int], 
                    end_chapter: Optional[int], online: bool = False):
        """Process documentation files and generate combined book"""
        try:
            if online:
                asyncio.run(self.process_online_docs())
                return
                
            logging.info(f"Processing documentation in {self.docs_dir}")
            logging.info(f"Mode: {mode}")
            
            # Setup keyboard listener for pause
            check_for_keypress()
            
            if mode == 'resume':
                start_chapter = self.current_chapter
                mode = 'all'
            elif mode == 'fix_links':
                from fix_markdown_links import fix_markdown_links
                fix_markdown_links(self.docs_dir)
                return
            elif mode == 'combine':
                self.processor.generate_combined_book()
                return
            
            # Process chapters first
            self.process_chapters(mode, start_chapter, end_chapter)
            
            # Then generate the combined book
            logging.info("Generating combined book...")
            self.processor.generate_combined_book()
            
            self.save_state()
            
            logging.info(f"Processing complete!")
            logging.info(f"Total chapters: {len(self.processor.chapters)}")
            logging.info(f"Total pages: {self.processor.state['total_pages']}")
            logging.info(f"Images referenced: {len(self.processor.image_refs)}")
            logging.info(f"Code blocks: {len(self.processor.formatter.code_blocks)}")
            
        except KeyboardInterrupt:
            logging.info("\nProcessing interrupted. Saving state...")
            self.save_state()
            self.processor.save_state()

    def process_chapters(self, mode: str, start_chapter: Optional[int], 
                        end_chapter: Optional[int]):
        """Process chapters based on mode and range"""
        logging.debug(f"Base directory: {self.docs_dir}")
        
        # Convert self.docs_dir to Path object
        docs_path = Path(self.docs_dir)
        
        for file_path in sorted(docs_path.rglob('*.md')):
            logging.debug(f"Processing file: {file_path}")
            while self.paused:
                time.sleep(1)
                
            if 'combined' in str(file_path):
                continue
                
            chapter_num = self.processor.get_chapter_for_file(file_path)
            if chapter_num is None:
                continue
                
            self.current_chapter = chapter_num
                
            # Skip if outside requested range
            if start_chapter and chapter_num < start_chapter:
                continue
            if end_chapter and chapter_num > end_chapter:
                continue
                
            # Skip if processing only new chapters
            if mode == 'new' and str(file_path) in self.processor.state['last_processed']:
                continue
                
            logging.info(f"Processing chapter {chapter_num}: {file_path.name}")
            self.processor.process_file(chapter_num, file_path)
            
            # Save state periodically
            if chapter_num % 5 == 0:
                self.save_state()
                self.processor.save_state()

    def toggle_pause(self):
        """Toggle processing pause state"""
        self.paused = not self.paused
        if self.paused:
            logging.info("\nProcessing paused. Press 'p' to resume.")
        else:
            logging.info("\nProcessing resumed.")

def main():
    manager = ProcessingManager()
    mode, start_chapter, end_chapter, online = manager.show_menu()
    
    print("\nProcessing controls:")
    print("- Press 'p' to pause/resume processing")
    print("- Press Ctrl+C to save and exit")
    
    time.sleep(2)  # Give user time to read instructions
    
    manager.process_docs(mode, start_chapter, end_chapter, online)

if __name__ == "__main__":
    main() 