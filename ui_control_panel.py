#!/usr/bin/env python3
"""
UI Control Panel for Peptide Scraper
A graphical interface for managing domains, lenses, and running the scraper
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import os
import subprocess
import threading
import logging
from pathlib import Path
import sys

# Import validation utilities
from utils.validators import (
    ensure_database_dir,
    validate_directory, validate_database, ValidationError
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PeptideScraperUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Peptide Scraper Control Panel")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # Configuration paths
        self.config_dir = Path("config")
        self.seeds_dir = Path("seeds")
        self.lenses_dir = Path("lenses")
        self.output_dir = Path("output")
        self.default_input_dir = Path("data/documents") if Path("data/documents").exists() else Path("input/pdfs")
        
        # Data storage
        self.domains = {}
        self.lenses = {}
        self.feeds_config = {}
        
        # Initialize UI
        self.create_widgets()
        self.load_configurations()
        
    def create_widgets(self):
        """Create the main UI layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Peptide Scraper Control Panel", 
                               font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=tk.W)
        
        # Configuration Section
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Domain Selection
        ttk.Label(config_frame, text="Domain:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.domain_var = tk.StringVar()
        self.domain_combo = ttk.Combobox(config_frame, textvariable=self.domain_var, width=30)
        self.domain_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        self.domain_combo.bind('<<ComboboxSelected>>', self.on_domain_change)
        
        # Lens Selection
        ttk.Label(config_frame, text="Lenses:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.lens_listbox = tk.Listbox(config_frame, selectmode=tk.MULTIPLE, height=4, width=30)
        self.lens_listbox.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Input Directory
        ttk.Label(config_frame, text="Input PDFs:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.input_dir_var = tk.StringVar(value=str(self.default_input_dir))
        self.input_dir_entry = ttk.Entry(config_frame, textvariable=self.input_dir_var, width=50)
        self.input_dir_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        ttk.Button(config_frame, text="Browse", command=self.browse_input_dir).grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # Database Path
        ttk.Label(config_frame, text="Database:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.db_var = tk.StringVar(value="db/runs.sqlite")
        self.db_entry = ttk.Entry(config_frame, textvariable=self.db_var, width=50)
        self.db_entry.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        ttk.Button(config_frame, text="Browse", command=self.browse_db).grid(row=2, column=3, sticky=tk.W, pady=(10, 0))
        
        # Controls Section
        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        controls_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Buttons
        self.run_button = ttk.Button(controls_frame, text="Run Scraper", command=self.run_scraper, style='Accent.TButton')
        self.run_button.grid(row=0, column=0, padx=(0, 10))
        
        self.export_button = ttk.Button(controls_frame, text="Export Results", command=self.export_results)
        self.export_button.grid(row=0, column=1, padx=(0, 10))
        
        self.rss_button = ttk.Button(controls_frame, text="Run RSS Ingest", command=self.run_rss_ingest)
        self.rss_button.grid(row=0, column=2, padx=(0, 10))
        
        self.status_button = ttk.Button(controls_frame, text="Check Status", command=self.check_status)
        self.status_button.grid(row=0, column=3, padx=(0, 10))
        
        # Progress Bar
        self.progress = ttk.Progressbar(controls_frame, orient=tk.HORIZONTAL, length=400, mode='indeterminate')
        self.progress.grid(row=1, column=0, columnspan=4, pady=(10, 0), sticky=(tk.W, tk.E))
        
        # Status Label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(controls_frame, textvariable=self.status_var, font=("Helvetica", 10))
        status_label.grid(row=2, column=0, columnspan=4, pady=(5, 0), sticky=tk.W)
        
        # Output Section
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        output_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(3, weight=1)
        
        # Output Text Area
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, width=100, wrap=tk.WORD)
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        # Footer
        footer_frame = ttk.Frame(main_frame)
        footer_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(footer_frame, text="Clear Output", command=self.clear_output).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(footer_frame, text="Save Output", command=self.save_output).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(footer_frame, text="Exit", command=self.root.quit).grid(row=0, column=2)
        
        # Configure styles
        style = ttk.Style()
        style.configure('Accent.TButton', background='#007bff', foreground='white')
        
    def load_configurations(self):
        """Load domains, lenses, and feeds configuration"""
        try:
            # Load domains
            self.load_domains()
            
            # Load lenses
            self.load_lenses()
            
            # Load feeds
            self.load_feeds()
            
            # Update UI
            self.update_domain_combo()
            self.update_lens_listbox()
            
            logger.info("Configurations loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
            messagebox.showerror("Configuration Error", f"Failed to load configurations: {e}")
    
    def load_domains(self):
        """Load available domains from config/domains and seeds/domains"""
        # First try config/domains (canonical location)
        config_domains_dir = self.config_dir / "domains"
        if config_domains_dir.exists():
            for domain_file in config_domains_dir.glob("*.json"):
                try:
                    with open(domain_file, 'r') as f:
                        domain_config = json.load(f)
                        self.domains[domain_config['id']] = domain_config
                except Exception as e:
                    logger.exception(f"Failed to load domain from config/domains {domain_file}: {e}")
        
        # Then try seeds/domains (legacy location) for backward compatibility
        seeds_domains_dir = self.seeds_dir / "domains"
        if seeds_domains_dir.exists():
            for domain_file in seeds_domains_dir.glob("*.json"):
                try:
                    with open(domain_file, 'r') as f:
                        domain_config = json.load(f)
                        # Only add if not already loaded from config/domains to avoid conflicts
                        if domain_config['id'] not in self.domains:
                            self.domains[domain_config['id']] = domain_config
                except Exception as e:
                    logger.exception(f"Failed to load domain from seeds/domains {domain_file}: {e}")
    
    def load_lenses(self):
        """Load available lenses from lenses directory"""
        if self.lenses_dir.exists():
            for lens_file in self.lenses_dir.glob("*_v1.py"):
                lens_name = lens_file.stem
                self.lenses[lens_name] = {
                    'name': lens_name.replace('_', ' ').title(),
                    'file': lens_file
                }
    
    def load_feeds(self):
        """Load RSS feeds configuration"""
        feeds_file = self.config_dir / "feeds.json"
        if feeds_file.exists():
            with open(feeds_file, 'r') as f:
                self.feeds_config = json.load(f)
    
    def update_domain_combo(self):
        """Update domain dropdown with available domains"""
        domain_names = [f"{domain['name']} ({domain_id})" for domain_id, domain in self.domains.items()]
        self.domain_combo['values'] = domain_names
        if domain_names:
            self.domain_combo.set(domain_names[0])
    
    def update_lens_listbox(self):
        """Update lens listbox with available lenses"""
        self.lens_listbox.delete(0, tk.END)
        for lens_name, lens_info in self.lenses.items():
            self.lens_listbox.insert(tk.END, lens_info['name'])
        
        # Select all lenses by default
        for i in range(self.lens_listbox.size()):
            self.lens_listbox.selection_set(i)
    
    def log_message(self, message):
        """Log message to output text area"""
        self.output_text.insert(tk.END, f"{message}\n")
        self.output_text.see(tk.END)

    def on_domain_change(self, event):
        """Handle domain selection change"""
        selected = self.domain_var.get()
        if selected:
            domain_id = selected.split('(')[-1].rstrip(')')
            if domain_id in self.domains:
                domain = self.domains[domain_id]
                self.status_var.set(f"Selected domain: {domain['name']}")
    
    def browse_input_dir(self):
        """Browse for input directory"""
        directory = filedialog.askdirectory(initialdir=self.input_dir_var.get() or str(self.default_input_dir))
        if directory:
            try:
                validated = validate_directory(directory, must_exist=True)
                self.input_dir_var.set(str(validated))
                self.log_message(f"✓ Input directory: {validated}")
            except ValidationError as e:
                messagebox.showerror("Invalid Directory", str(e))
    
    def browse_db(self):
        """Browse for database file"""
        filename = filedialog.asksaveasfilename(
            initialdir="db",
            defaultextension=".sqlite",
            filetypes=[("SQLite files", "*.sqlite"), ("All files", "*.*")]
        )
        if filename:
            try:
                # Check if file exists first
                if os.path.exists(filename):
                    # File exists, validate it
                    validated = validate_database(filename)
                    self.db_var.set(str(validated))
                    self.log_message(f"✓ Database file: {validated}")
                else:
                    # File doesn't exist, validate extension and create parent directory
                    db_path = Path(filename)
                    if db_path.suffix.lower() not in ['.db', '.sqlite', '.sqlite3']:
                        raise ValidationError(f"Invalid database extension: {db_path.suffix}")
                    
                    # Ensure parent directory exists
                    db_path = ensure_database_dir(db_path)
                    
                    self.db_var.set(str(db_path))
                    self.log_message(f"✓ New database file: {db_path}")
                    
            except ValidationError as e:
                messagebox.showerror("Invalid Database", str(e))
    
    def run_scraper(self):
        """Run the main scraper with selected configuration"""
        # Get selected domain
        selected_domain = self.domain_var.get()
        if not selected_domain:
            messagebox.showwarning("Warning", "Please select a domain")
            return
        
        domain_id = selected_domain.split('(')[-1].rstrip(')')
        
        # Get selected lenses
        selected_indices = self.lens_listbox.curselection()
        selected_lenses = [self.lens_listbox.get(i) for i in selected_indices]
        
        # Get paths
        input_dir = self.input_dir_var.get()
        db_path = self.db_var.get()
        
        # Validate paths
        if not Path(input_dir).exists():
            messagebox.showwarning("Warning", f"Input directory does not exist: {input_dir}")
            return
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run scraper in background thread
        thread = threading.Thread(target=self._run_scraper_thread, args=(domain_id, input_dir, db_path, selected_lenses))
        thread.daemon = True
        thread.start()
        
        self.progress.start()
        self.status_var.set("Running scraper...")
        self.run_button.config(state='disabled')
    
    def _run_scraper_thread(self, domain_id, input_dir, db_path, selected_lenses):
        """Run scraper in background thread"""
        try:
            # Import and run the scraper
            from utils.run_engine import main as run_scraper_main
            
            # Run the scraper with selected lenses
            run_scraper_main(domain=domain_id, input_dir=Path(input_dir), db_path=Path(db_path), lenses=selected_lenses)
            
            # Update UI on completion
            self.root.after(0, self._scraper_complete, "Scraper completed successfully")
            
        except Exception as e:
            logger.exception("Scraper error")
            self.root.after(0, self._scraper_complete, f"Scraper failed: {e}")
    
    def _scraper_complete(self, message):
        """Handle scraper completion"""
        self.progress.stop()
        self.status_var.set(message)
        self.run_button.config(state='normal')
        messagebox.showinfo("Complete", message)
    
    def export_results(self):
        """Export results using the export script"""
        try:
            # Get selected domain
            selected_domain = self.domain_var.get()
            if not selected_domain:
                messagebox.showwarning("Warning", "Please select a domain")
                return
            
            domain_id = selected_domain.split('(')[-1].rstrip(')')
            
            # Validate database path
            db_path = self.db_var.get()
            if not db_path or not db_path.strip():
                messagebox.showwarning("Warning", "Please specify a database path")
                return
            
            # Run dual-lens export script with selected domain
            result = subprocess.run([sys.executable, "utils/export/export_dual_lens.py",
                                   str(db_path), domain_id],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self.output_text.insert(tk.END, f"Export completed for {domain_id}:\n{result.stdout}\n")
                messagebox.showinfo("Export Complete", f"Results exported successfully for {domain_id}")
            else:
                self.output_text.insert(tk.END, f"Export error:\n{result.stderr}\n")
                messagebox.showerror("Export Error", result.stderr)
                
        except Exception as e:
            logger.exception("Export error")
            messagebox.showerror("Export Error", str(e))
    
    def run_rss_ingest(self):
        """Run RSS feed ingestion"""
        try:
            feeds_path = self.config_dir / "feeds.json"
            db_path = self.db_var.get()

            # Run RSS ingest script with UI-configured feeds and DB paths
            result = subprocess.run([
                sys.executable,
                "run_rss_ingest.py",
                "--feeds",
                str(feeds_path),
                "--db",
                str(db_path),
            ],
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self.output_text.insert(tk.END, f"RSS ingest completed:\n{result.stdout}\n")
                messagebox.showinfo("RSS Ingest Complete", "RSS feeds processed successfully")
            else:
                self.output_text.insert(tk.END, f"RSS ingest error:\n{result.stderr}\n")
                messagebox.showerror("RSS Ingest Error", result.stderr)
                
        except Exception as e:
            logger.exception("RSS ingest error")
            messagebox.showerror("RSS Ingest Error", str(e))
    
    def check_status(self):
        """Check system status"""
        status_info = []
        
        # Check input directory
        input_dir = Path(self.input_dir_var.get())
        if input_dir.exists():
            pdf_count = len(list(input_dir.glob("*.pdf")))
            status_info.append(f"Input directory: {input_dir} ({pdf_count} PDFs)")
        else:
            status_info.append(f"Input directory: {input_dir} (NOT FOUND)")
        
        # Check database
        db_path = Path(self.db_var.get())
        if db_path.exists():
            status_info.append(f"Database: {db_path} (EXISTS)")
        else:
            status_info.append(f"Database: {db_path} (NOT FOUND)")
        
        # Check domains
        status_info.append(f"Loaded domains: {len(self.domains)}")
        
        # Check lenses
        status_info.append(f"Loaded lenses: {len(self.lenses)}")
        
        # Display status
        status_text = "\n".join(status_info)
        self.output_text.insert(tk.END, f"System Status:\n{status_text}\n\n")
        messagebox.showinfo("System Status", status_text)
    
    def clear_output(self):
        """Clear output text area"""
        self.output_text.delete(1.0, tk.END)
    
    def save_output(self):
        """Save output to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(self.output_text.get(1.0, tk.END))
            messagebox.showinfo("Save Complete", f"Output saved to {filename}")

def main():
    """Main entry point"""
    root = tk.Tk()
    PeptideScraperUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()