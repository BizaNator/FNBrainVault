"""
Example script showing how to use webmark_uefn.py and combine_docs.py together
"""

import asyncio
from webmark_uefn import main as webmark_main
from combine_docs import DocumentProcessor

async def process_documentation(force_download: bool = False):
    """
    Process UEFN documentation end-to-end:
    1. Download and process documentation
    2. Generate combined book
    """
    # Step 1: Download and process documentation
    print("Downloading and processing documentation...")
    await webmark_main(force_download=force_download, download_images=True)
    
    # Step 2: Generate combined book
    print("\nGenerating combined book...")
    processor = DocumentProcessor("./downloaded_docs")
    processor.generate_combined_book()
    
    print("\nDocumentation processing complete!")
    print("- Check ./downloaded_docs for individual markdown files")
    print("- Check ./downloaded_docs/combined for the combined book")

if __name__ == "__main__":
    # Run the async process
    asyncio.run(process_documentation(force_download=False)) 