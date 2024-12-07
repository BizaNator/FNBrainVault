# UEFN Documentation Processor

## Overview

The UEFN Documentation Processor is a tool for processing and combining documentation files with advanced control features including pause/resume functionality and selective chapter processing.

## Usage

### Basic Usage

```bash
python process_existing.py
```

### Interactive Menu Options

1. Process all chapters
   - Processes entire documentation set
   - Generates complete combined book

2. Process new chapters only
   - Checks for unprocessed chapters
   - Updates existing combined book

3. Process specific chapter range
   - Select start and end chapter numbers
   - Process subset of documentation

4. Resume from last position
   - Continues from last processed chapter
   - Maintains processing state

5. Exit
   - Saves state and exits program

### Controls During Processing

- Press 'p' to pause/resume processing
- Press Ctrl+C to save and exit gracefully

## API

### ProcessingManager

```python
class ProcessingManager:
    def __init__(self, docs_dir: str = "./downloaded_docs"):
        """Initialize processing manager with docs directory"""
```

#### Methods

``` python
def load_state(self):
    """Load processing state from .processing_state.json"""

def save_state(self):
    """Save current processing state"""

def show_menu(self) -> tuple[str, Optional[int], Optional[int]]:
    """Display interactive menu and get user choice"""

def process_docs(self, mode: str, start_chapter: Optional[int] = None, 
                end_chapter: Optional[int] = None):
    """Process documentation based on selected mode"""

def process_chapters(self, mode: str, start_chapter: Optional[int], 
                    end_chapter: Optional[int]):
    """Process chapters based on mode and range"""

def toggle_pause(self):
    """Toggle processing pause state"""
```

## Integration

### With DocumentProcessor

```python
from combine_docs import DocumentProcessor

processor = DocumentProcessor(docs_dir)
manager = ProcessingManager(docs_dir)
```

### With BookFormatter

```python
from book_formatter import BookFormatter

formatter = BookFormatter(docs_dir)
```

## Best Practices

1. State Management
   - Regular state saves during processing
   - Automatic recovery from interruptions
   - Progress tracking between sessions

2. Error Handling
   - Graceful handling of interruptions
   - State preservation on errors
   - Detailed error logging

3. Processing Modes
   - Use selective processing for large documentation sets
   - Resume capability for interrupted sessions
   - Incremental updates for efficiency

## Class Diagram

``` mermaid
classDiagram
    class ProcessingManager {
        +docs_dir: str
        +state_file: Path
        +processor: DocumentProcessor
        +paused: bool
        +current_chapter: int
        +load_state()
        +save_state()
        +show_menu()
        +process_docs()
        +process_chapters()
        +toggle_pause()
    }
``` 