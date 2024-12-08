import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import asyncio
import os
from pathlib import Path
import json
from typing import Dict, Optional
import logging
from datetime import datetime

# Import your existing modules
from webmark_uefn import main as scraper_main
from process_existing import ProcessingManager
from config_manager import ConfigManager

class FNBrainVault:
    def __init__(self, root):
        self.root = root
        self.root.title("FNBrainVault - Documentation Scraper")
        self.root.geometry("800x600")
        
        # Initialize configuration
        self.config_manager = ConfigManager()
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Create tabs
        self.scraper_tab = ttk.Frame(self.notebook)
        self.processor_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.scraper_tab, text="Scraper")
        self.notebook.add(self.processor_tab, text="Processor")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Initialize tabs
        self.init_scraper_tab()
        self.init_processor_tab()
        self.init_settings_tab()
        
        # Setup logging
        self.setup_logging()

    def init_scraper_tab(self):
        """Initialize the scraper tab"""
        frame = ttk.LabelFrame(self.scraper_tab, text="Scraper Configuration", padding=10)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Initialize url_var before calling update_presets
        self.url_var = tk.StringVar()
        
        # Preset Selection
        ttk.Label(frame, text="Documentation Preset:").grid(row=0, column=0, sticky='w', pady=5)
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(frame, textvariable=self.preset_var, state="readonly")
        self.preset_combo.grid(row=0, column=1, columnspan=2, sticky='ew', pady=5)
        
        # Load presets
        self.update_presets()
        self.preset_combo.bind('<<ComboboxSelected>>', self.on_preset_selected)
        
        # Add Preset Button
        ttk.Button(frame, text="Add Preset", command=self.show_add_preset_dialog).grid(
            row=0, column=3, padx=5, pady=5)
        
        # URL Display
        ttk.Label(frame, text="Base URL:").grid(row=1, column=0, sticky='w', pady=5)
        url_entry = ttk.Entry(frame, textvariable=self.url_var, state="readonly")
        url_entry.grid(row=1, column=1, columnspan=2, sticky='ew', pady=5)
        
        # Force Download Option
        self.force_download_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Force Download", variable=self.force_download_var).grid(row=2, column=0, sticky='w', pady=5)
        
        # Download Images Option
        self.download_images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Download Images", variable=self.download_images_var).grid(row=2, column=1, sticky='w', pady=5)
        
        # Progress Frame
        progress_frame = ttk.LabelFrame(frame, text="Progress", padding=10)
        progress_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=10)
        
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(fill='x')
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=5)
        
        # Control Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="Start Scraping", command=self.start_scraping).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Stop", command=self.stop_scraping).pack(side='left', padx=5)
        
        # Log Frame
        log_frame = ttk.LabelFrame(frame, text="Log", padding=10)
        log_frame.grid(row=5, column=0, columnspan=3, sticky='nsew', pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, width=70)
        self.log_text.pack(fill='both', expand=True)
        
        # Configure grid weights
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

    def update_presets(self):
        """Update the presets dropdown"""
        presets = self.config_manager.get_presets("documentation")
        self.preset_combo['values'] = list(presets.keys())
        if presets:
            self.preset_combo.set(list(presets.keys())[0])
            self.on_preset_selected()

    def on_preset_selected(self, event=None):
        """Handle preset selection"""
        preset_name = self.preset_var.get()
        preset = self.config_manager.get_presets("documentation").get(preset_name)
        if preset:
            self.url_var.set(preset["base_url"])

    def show_add_preset_dialog(self):
        """Show dialog to add new preset"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Preset")
        dialog.geometry("400x300")
        
        # Add form fields for new preset
        ttk.Label(dialog, text="Name:").pack(pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var).pack(fill='x', padx=5)
        
        ttk.Label(dialog, text="Base URL:").pack(pady=5)
        url_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=url_var).pack(fill='x', padx=5)
        
        ttk.Label(dialog, text="Link Pattern:").pack(pady=5)
        pattern_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=pattern_var).pack(fill='x', padx=5)
        
        ttk.Label(dialog, text="Description:").pack(pady=5)
        desc_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=desc_var).pack(fill='x', padx=5)
        
        def save_preset():
            self.config_manager.add_preset(
                "documentation",
                name_var.get(),
                url_var.get(),
                pattern_var.get(),
                desc_var.get()
            )
            self.update_presets()
            dialog.destroy()
        
        ttk.Button(dialog, text="Save", command=save_preset).pack(pady=10)

    def init_processor_tab(self):
        """Initialize the processor tab"""
        frame = ttk.LabelFrame(self.processor_tab, text="Document Processing", padding=10)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Processing Options
        ttk.Label(frame, text="Processing Mode:").grid(row=0, column=0, sticky='w', pady=5)
        self.process_mode_var = tk.StringVar(value="all")
        modes = [
            ("Process All Chapters", "all"),
            ("Process New Chapters", "new"),
            ("Process Range", "range"),
            ("Resume Last Position", "resume"),
            ("Update Online Docs", "online"),
            ("Fix Markdown Links", "fix_links"),
            ("Generate Combined Book", "combine")
        ]
        
        for i, (text, mode) in enumerate(modes):
            ttk.Radiobutton(frame, text=text, variable=self.process_mode_var, value=mode).grid(row=i+1, column=0, sticky='w', pady=2)
        
        # Chapter Range Frame
        range_frame = ttk.LabelFrame(frame, text="Chapter Range", padding=5)
        range_frame.grid(row=1, column=1, rowspan=2, sticky='nsew', padx=10)
        
        ttk.Label(range_frame, text="Start:").grid(row=0, column=0, pady=2)
        self.start_chapter_var = tk.StringVar()
        ttk.Entry(range_frame, textvariable=self.start_chapter_var, width=10).grid(row=0, column=1, pady=2)
        
        ttk.Label(range_frame, text="End:").grid(row=1, column=0, pady=2)
        self.end_chapter_var = tk.StringVar()
        ttk.Entry(range_frame, textvariable=self.end_chapter_var, width=10).grid(row=1, column=1, pady=2)
        
        # Control Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Start Processing", command=self.start_processing).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Pause/Resume", command=self.toggle_processing).pack(side='left', padx=5)
        
        # Progress Display
        self.process_progress_var = tk.StringVar(value="Ready")
        ttk.Label(frame, textvariable=self.process_progress_var).grid(row=9, column=0, columnspan=2, sticky='w', pady=5)
        
        # Configure grid weights
        frame.columnconfigure(1, weight=1)

    def init_settings_tab(self):
        """Initialize the settings tab"""
        frame = ttk.LabelFrame(self.settings_tab, text="Configuration Settings", padding=10)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Output Directory
        ttk.Label(frame, text="Output Directory:").grid(row=0, column=0, sticky='w', pady=5)
        self.output_dir_var = tk.StringVar(value=self.config_manager.get_setting("output_dir"))
        ttk.Entry(frame, textvariable=self.output_dir_var).grid(row=0, column=1, sticky='ew', pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_directory("output_dir")).grid(row=0, column=2, padx=5)
        
        # Images Directory
        ttk.Label(frame, text="Images Directory:").grid(row=1, column=0, sticky='w', pady=5)
        self.images_dir_var = tk.StringVar(value=self.config_manager.get_setting("images_dir"))
        ttk.Entry(frame, textvariable=self.images_dir_var).grid(row=1, column=1, sticky='ew', pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_directory("images_dir")).grid(row=1, column=2, padx=5)
        
        
        # Other Settings
        ttk.Label(frame, text="Max Concurrent Downloads:").grid(row=2, column=0, sticky='w', pady=5)
        self.max_concurrent_var = tk.StringVar(value=str(self.config_manager.get_setting("max_concurrent")))
        ttk.Entry(frame, textvariable=self.max_concurrent_var, width=10).grid(row=2, column=1, sticky='w', pady=5)
        
        # Browser settings
        browser_frame = ttk.LabelFrame(frame, text="Browser Settings", padding=5)
        browser_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=10)
        
        ttk.Label(frame, text="Rate Limit Delay (seconds):").grid(row=3, column=0, sticky='w', pady=5)
        self.rate_limit_var = tk.StringVar(value=str(self.config_manager.get_setting("rate_limit_delay")))
        ttk.Entry(frame, textvariable=self.rate_limit_var, width=10).grid(row=3, column=1, sticky='w', pady=5)
        # Browser language
        ttk.Label(browser_frame, text="Browser Language:").pack(anchor='w')
        self.browser_lang_var = tk.StringVar(value=self.config_manager.get_setting("browser_lang"))
        ttk.Entry(browser_frame, textvariable=self.browser_lang_var).pack(fill='x')

        # Headless mode
        self.headless_var = tk.BooleanVar(value=self.config_manager.get_setting("headless"))
        ttk.Checkbutton(browser_frame, text="Headless Mode", variable=self.headless_var).pack(anchor='w')
        
        # Browser language
        ttk.Label(browser_frame, text="Browser Language:").pack(anchor='w')
        self.browser_lang_var = tk.StringVar(value=self.config_manager.get_setting("browser_lang"))
        ttk.Entry(browser_frame, textvariable=self.browser_lang_var).pack(fill='x')
        
        # Save button
        ttk.Button(frame, text="Save Settings", command=self.save_settings).grid(row=4, column=0, columnspan=3, pady=20)
        
        # Configure grid weights
        frame.columnconfigure(1, weight=1)

    def browse_directory(self, setting_name: str):
        """Open directory browser and update setting"""
        directory = filedialog.askdirectory(initialdir=self.config_manager.get_setting(setting_name))
        if directory:
            if setting_name == "output_dir":
                self.output_dir_var.set(directory)
            elif setting_name == "images_dir":
                self.images_dir_var.set(directory)

    def save_settings(self):
        """Save current settings to config"""
        try:
            # Update existing settings
            self.config_manager.update_setting("output_dir", self.output_dir_var.get())
            self.config_manager.update_setting("images_dir", self.images_dir_var.get())
            self.config_manager.update_setting("max_concurrent", int(self.max_concurrent_var.get()))
            self.config_manager.update_setting("rate_limit_delay", float(self.rate_limit_var.get()))
            
            # Add browser settings
            self.config_manager.update_setting("headless", self.headless_var.get())
            self.config_manager.update_setting("browser_lang", self.browser_lang_var.get())
            
            self.config_manager.save_config()
            messagebox.showinfo("Success", "Settings saved successfully!")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid setting value: {str(e)}")

    def setup_logging(self):
        """Setup logging to both file and UI"""
        class TextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                self.text_widget.insert('end', msg + '\n')
                self.text_widget.see('end')
        
        # Configure logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Add handler for UI
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(text_handler)

    async def run_scraper(self):
        """Run the scraper asynchronously"""
        try:
            self.progress_bar.start()
            self.progress_var.set("Scraping in progress...")
            
            # Pass both URL and config manager to scraper
            await scraper_main(
                base_url=self.url_var.get(),
                force_download=self.force_download_var.get(),
                download_images=self.download_images_var.get(),
                config_manager=self.config_manager
            )
            
            self.progress_var.set("Scraping completed!")
        except Exception as e:
            self.progress_var.set(f"Error: {str(e)}")
            logging.error(f"Scraping error: {str(e)}")
        finally:
            self.progress_bar.stop()

    def start_scraping(self):
        """Start the scraping process"""
        asyncio.run(self.run_scraper())

    def stop_scraping(self):
        """Stop the scraping process"""
        # Implement stop functionality
        self.progress_var.set("Scraping stopped")
        self.progress_bar.stop()

    def start_processing(self):
        """Start the document processing"""
        mode = self.process_mode_var.get()
        start_chapter = None
        end_chapter = None
        
        if mode == "range":
            try:
                start_chapter = int(self.start_chapter_var.get())
                end_chapter = int(self.end_chapter_var.get())
            except ValueError:
                messagebox.showerror("Error", "Please enter valid chapter numbers")
                return
        
        processor = ProcessingManager(self.output_dir_var.get())
        processor.process_docs(mode, start_chapter, end_chapter, mode == "online")

    def toggle_processing(self):
        """Toggle processing pause state"""
        # Implement pause/resume functionality
        pass

def main():
    root = tk.Tk()
    app = FNBrainVault(root)
    root.mainloop()

if __name__ == "__main__":
    main() 