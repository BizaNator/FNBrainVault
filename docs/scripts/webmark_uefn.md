# WebMark UEFN Documentation Scraper


UEFN Documentation Scraper and Processor
======================================

This module provides functionality to scrape, download, and process UEFN (Unreal Editor for Fortnite)
documentation into a well-organized markdown format with chapter organization.

## System Architecture 

```mermaid
graph TD
A[Main Script] --> B[DownloadManager]
A --> C[Browser Session]
A --> D[Content Processing]
B --> B1[State Management]
B --> B2[Error Handling]
B --> B3[Index Generation]
C --> C1[Page Navigation]
C --> C2[Link Extraction]
C --> C3[Content Scraping]
D --> D1[Markdown Conversion]
D --> D2[Image Processing]
D --> D3[File Organization]
```

## Overview
The WebMark UEFN script is the main component responsible for scraping, processing, and organizing UEFN documentation from Epic Games' website.

Usage:
------
### 1. Standalone usage:

```python
from webmark_uefn import main
import asyncio

#### Basic usage

asyncio.run(main())

## With options

asyncio.run(main(force_download=True, download_images=True))
```

### 2. Usage with combine_docs.py:

```python
from webmark_uefn import DocumentProcessor
from combine_docs import DocumentProcessor as CombineProcessor

# First download and process the documentation
async def process_docs():
await main(force_download=False, download_images=True)

# Then combine the processed documents
doc_processor = CombineProcessor("./downloaded_docs")
doc_processor.generate_combined_book()
```


Configuration:
-------------
- BASE_URL: The root URL for UEFN documentation
- OUTPUT_DIR: Directory where downloaded docs will be saved
- MAX_CONCURRENT_DOWNLOADS: Limit on simultaneous downloads
- RATE_LIMIT_DELAY: Delay between requests to avoid rate limiting

Requirements:
------------
- Python 3.7+
- Dependencies listed in requirements.txt

Features:
---------
- Automatic chapter organization
- Image downloading and optimization
- Internal link processing
- Markdown conversion
- YAML frontmatter generation
- Progress tracking and resume capability
"""



## Core Components

### DownloadState Class
```mermaid
classDiagram
class DownloadState {
+completed_urls: Set[str]
+failed_downloads: Dict
+retry_queue: List[str]
+save(output_dir)
+load(output_dir)
}
```

**Purpose**: Manages the state of downloaded content and provides persistence.



### DownloadManager Class
```mermaid
classDiagram
class DownloadManager {
+output_dir: str
+max_retries: int
+retry_delay: int
+download_times: List
+processed_urls: Set
+failed_urls: Set
+generate_index()
+generate_print_ready_version()
+retry_failed_downloads()
}
```

**Purpose**: Manages the download process, including retries, error handling, and state management.

## Key Functions

### scrape()
**Purpose**: Wrapper for the main scraping function.
**Parameters**:
- base_url (str): The base URL to start scraping from.
- force_download (bool): Force redownload of existing content.
- download_images (bool): Enable/disable image downloading.

### main()
**Purpose**: Entry point for the scraping process.
**Parameters**:
- force_download (bool): Force redownload of existing content.
- download_images (bool): Enable/disable image downloading.

### get_links_and_download()
**Purpose**: Recursively discovers and processes documentation pages
**Flow**:
```mermaid
sequenceDiagram
participant M as Main
participant P as Page
participant D as Downloader
M->>P: Navigate to URL
P->>P: Extract Links
P->>D: Download Content
D->>P: Process Child Links
P->>M: Return All Links
```

## Error Handling
The script implements comprehensive error handling for:
- Network failures (502, 504)
- Recursion limits
- Content parsing errors
- Browser session issues

## Usage

### Basic Usage

```bash
python webmark_uefn.py
```

### Advanced Options

```bash
python webmark_uefn.py --force-download --no-images
```

## Dependencies

```mermaid
graph TD
    A[webmark_uefn.py] --> B[nodriver]
    A --> C[aiohttp]
    A --> D[BeautifulSoup4]
    A --> E[markdownify]
    A --> F[PIL]
```

## Output Structure
```
/downloaded_docs
├── documentation/
│   └── en-us/
│       └── uefn/
├── images/
├── index.md
└── .download_state
```


