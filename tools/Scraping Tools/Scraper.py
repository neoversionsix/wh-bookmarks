import requests
import os
import time
import shutil
import re
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

# --- Core Scraping Logic ---

def sanitize_filename(filename):
    """
    Cleans a string to be used as a valid filename.
    """
    decoded_filename = unquote(filename)
    sanitized = re.sub(r'[^\w._-]', '-', decoded_filename)
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')
    return sanitized

def clean_html(soup, is_main_page=False):
    """
    Removes unwanted elements from a BeautifulSoup object, using the more
    specific rules from the original Cerner scraper.
    """
    # Remove elements by their ID
    ids_to_remove = [
        'header', 'header-precursor', 'main-header', 'labels-section',
        'comments-section', 'footer', 'dbContext-wrapper', 'space-tools-web-items'
    ]
    for element_id in ids_to_remove:
        element = soup.find(id=element_id)
        if element:
            element.decompose()

    # Remove elements by their class name
    classes_to_remove = [
        'ia-splitter-left', 'dbNav', 'page-metadata', 'published-version'
    ]
    for class_name in classes_to_remove:
        for element in soup.find_all(class_=class_name):
            element.decompose()

    # Remove the hidden parameter fieldsets
    for fieldset in soup.find_all('fieldset', class_='parameters hidden'):
        fieldset.decompose()

    # Remove all <section> tags (used for pop-up dialogs)
    for section in soup.find_all('section'):
        section.decompose()

    # Remove all script, link, and meta tags
    for s in soup.select('script, link, meta'):
        s.decompose()
        
    # Adjust the main content margin now that the sidebar is gone
    main_content = soup.find('main', id='main')
    if main_content:
        main_content.attrs.pop('style', None)

    # Remove the borders from the code example boxes
    for preformatted_box in soup.find_all('div', class_='preformatted'):
        preformatted_box.attrs.pop('style', None)

    # For the individual function pages, remove all links within the content
    if not is_main_page:
        content_div = soup.find('div', id='main-content')
        if content_div:
            for a in content_div.find_all('a'):
                a.unwrap()

    return soup

def scrape_website(start_url, scrape_method, text_pattern, container_class, output_dir, log_callback):
    """
    Scrapes a website based on the selected method.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    session.headers.update(headers)

    try:
        log_callback(f"Fetching main page: {start_url}")
        response = session.get(start_url)
        response.raise_for_status()
        
        main_soup = BeautifulSoup(response.text, 'html.parser')
        links = []

        # Choose link finding strategy based on scrape_method
        if scrape_method == "text":
            log_callback(f"Searching for links after text matching pattern: '{text_pattern}'")
            intro_text_element = main_soup.find(string=re.compile(text_pattern, re.IGNORECASE))
            if intro_text_element:
                log_callback("Found introductory text.")
                parent = intro_text_element.find_parent()
                link_container = parent.find_next_sibling(['ul', 'ol', 'div', 'p'])
                if link_container:
                    links = link_container.find_all('a', href=True)
                    log_callback(f"Found container for links: <{link_container.name}>")
                else:
                    log_callback("Error: Found intro text, but couldn't find a following list or div.")
            else:
                log_callback(f"Error: Could not find text matching pattern.")
        
        elif scrape_method == "container":
            log_callback(f"Searching for links inside containers with class: '{container_class}'")
            link_containers = main_soup.find_all('div', class_=container_class)
            if link_containers:
                for container in link_containers:
                    links.extend(container.find_all('a', href=True))
                log_callback(f"Found {len(link_containers)} container(s).")
            else:
                log_callback("Error: Could not find any containers with that class name.")

        if not links:
            log_callback("\nScraping stopped: No links found to process.")
            return

        log_callback(f"Found {len(links)} links to process.")

        for i, link in enumerate(links):
            time.sleep(0.5)
            href = link['href']
            absolute_url = urljoin(start_url, href)
            
            if urlparse(absolute_url).netloc != urlparse(start_url).netloc:
                log_callback(f"  - Skipping external link: {absolute_url}")
                continue

            try:
                log_callback(f"  ({i+1}/{len(links)}) Fetching: {absolute_url.split('/')[-1]}")
                # Use the same session headers for subsequent requests
                page_response = session.get(absolute_url, headers={'Referer': start_url})
                page_response.raise_for_status()
                
                page_soup = BeautifulSoup(page_response.text, 'html.parser')
                cleaned_page_soup = clean_html(page_soup, is_main_page=False)
                
                path_part = os.path.basename(urlparse(absolute_url).path)
                filename = sanitize_filename(path_part) + ".html"
                file_path = os.path.join(output_dir, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(cleaned_page_soup))
                
                link['href'] = filename
                
            except requests.exceptions.RequestException as e:
                log_callback(f"    - ERROR fetching {absolute_url}: {e}")
                link['href'] = '#'
                link.string = f"[DOWNLOAD FAILED] {link.string}"

        log_callback("\nCleaning and saving the main index page...")
        cleaned_main_soup = clean_html(main_soup, is_main_page=True)
        
        main_page_path = os.path.join(output_dir, "index.html")
        with open(main_page_path, 'w', encoding='utf-8') as f:
            f.write(str(cleaned_main_soup))
        log_callback(f"\nScraping complete! Files saved in:\n{output_dir}")

    except requests.exceptions.RequestException as e:
        log_callback(f"FATAL ERROR: Could not fetch the main URL {start_url}. {e}")
    except Exception as e:
        log_callback(f"An unexpected error occurred: {e}")


# --- GUI Application Class ---

class ScraperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Web Page Scraper")
        self.geometry("700x650") # Increased height for new widgets
        self.configure(bg='#f0f0f0')
        self.output_dir = ""

        style = ttk.Style(self)
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 10))
        style.configure('TButton', font=('Helvetica', 10, 'bold'))
        style.configure('TEntry', font=('Helvetica', 10))
        style.configure('TFrame', background='#f0f0f0')
        style.configure('Path.TLabel', foreground='grey')
        style.configure('TRadiobutton', background='#f0f0f0', font=('Helvetica', 10))

        main_frame = ttk.Frame(self, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Scrape Method Selection ---
        method_frame = ttk.LabelFrame(main_frame, text="Scraping Method", padding="10 5")
        method_frame.pack(fill=tk.X, pady=5)
        
        self.scrape_method_var = tk.StringVar(value="text")
        
        text_radio = ttk.Radiobutton(method_frame, text="By Introductory Text", variable=self.scrape_method_var, value="text", command=self.toggle_inputs)
        text_radio.pack(side=tk.LEFT, padx=10)
        
        container_radio = ttk.Radiobutton(method_frame, text="By Container Class", variable=self.scrape_method_var, value="container", command=self.toggle_inputs)
        container_radio.pack(side=tk.LEFT, padx=10)

        # --- Input fields frame ---
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="Start URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.url_entry = ttk.Entry(input_frame, width=80)
        self.url_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        self.url_entry.insert(0, "https://wiki.cerner.com/display/public/1101discernHP/Programming+Constructs+Using+Discern+Explorer")

        self.text_label = ttk.Label(input_frame, text="Introductory Text (Regex):")
        self.text_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.text_entry = ttk.Entry(input_frame, width=80)
        self.text_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.text_entry.insert(0, "Click each of the following Programming Constructs to learn more")
        
        self.container_label = ttk.Label(input_frame, text="Container Class Name:")
        self.container_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.container_entry = ttk.Entry(input_frame, width=80)
        self.container_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        self.container_entry.insert(0, "panelContent")

        input_frame.columnconfigure(1, weight=1)

        # --- Output folder selection frame ---
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=(10, 5))
        
        ttk.Label(output_frame, text="Output Folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.output_dir_var = tk.StringVar(value="No folder selected")
        self.output_label = ttk.Label(output_frame, textvariable=self.output_dir_var, style='Path.TLabel', anchor='w')
        self.output_label.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        browse_button = ttk.Button(output_frame, text="Browse...", command=self.select_output_folder)
        browse_button.grid(row=0, column=2, sticky=tk.E, padx=5, pady=2)
        output_frame.columnconfigure(1, weight=1)

        # --- Control buttons frame ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        self.scrape_button = ttk.Button(button_frame, text="Start Scraping", command=self.start_scraping_thread)
        self.scrape_button.pack(side=tk.LEFT, padx=5)

        # --- Log display ---
        ttk.Label(main_frame, text="Log Output:").pack(anchor=tk.W, padx=5)
        self.log_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=20, font=("Courier New", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_area.configure(state='disabled')

        self.toggle_inputs() # Set initial state of inputs

    def toggle_inputs(self):
        """Enables/disables input fields based on radio button selection."""
        method = self.scrape_method_var.get()
        if method == "text":
            self.text_entry.config(state=tk.NORMAL)
            self.text_label.config(state=tk.NORMAL)
            self.container_entry.config(state=tk.DISABLED)
            self.container_label.config(state=tk.DISABLED)
        elif method == "container":
            self.text_entry.config(state=tk.DISABLED)
            self.text_label.config(state=tk.DISABLED)
            self.container_entry.config(state=tk.NORMAL)
            self.container_label.config(state=tk.NORMAL)

    def select_output_folder(self):
        directory = filedialog.askdirectory(title="Select Folder to Save Files")
        if directory:
            self.output_dir = directory
            self.output_dir_var.set(directory)
            self.output_label.configure(style='TLabel')

    def log(self, message):
        def append():
            self.log_area.configure(state='normal')
            self.log_area.insert(tk.END, message + '\n')
            self.log_area.configure(state='disabled')
            self.log_area.see(tk.END)
        self.after(0, append)

    def start_scraping_thread(self):
        start_url = self.url_entry.get().strip()
        scrape_method = self.scrape_method_var.get()
        text_pattern = self.text_entry.get().strip()
        container_class = self.container_entry.get().strip()
        output_dir = self.output_dir

        if not start_url:
            messagebox.showerror("Input Error", "Please provide a Start URL.")
            return
        if scrape_method == "text" and not text_pattern:
            messagebox.showerror("Input Error", "Please provide the Introductory Text.")
            return
        if scrape_method == "container" and not container_class:
            messagebox.showerror("Input Error", "Please provide the Container Class Name.")
            return
        if not output_dir:
            messagebox.showerror("Input Error", "Please select an output folder.")
            return
            
        self.log_area.configure(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state='disabled')
        self.scrape_button.config(state=tk.DISABLED)

        thread = threading.Thread(
            target=self.run_scrape_task,
            args=(start_url, scrape_method, text_pattern, container_class, output_dir)
        )
        thread.daemon = True
        thread.start()

    def run_scrape_task(self, start_url, scrape_method, text_pattern, container_class, output_dir):
        try:
            scrape_website(start_url, scrape_method, text_pattern, container_class, output_dir, self.log)
        except Exception as e:
            self.log(f"An unexpected error occurred in the scraping thread: {e}")
        finally:
            self.after(0, lambda: self.scrape_button.config(state=tk.NORMAL))


if __name__ == "__main__":
    app = ScraperApp()
    app.mainloop()
