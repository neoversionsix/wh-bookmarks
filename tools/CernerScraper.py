import requests
import os
import time
import shutil
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

def sanitize_filename(filename):
    """
    Cleans a string to be used as a valid filename.
    It decodes URL-encoded characters and replaces special characters with hyphens.

    Args:
        filename (str): The original filename or string to clean.

    Returns:
        str: A sanitized, file-safe string.
    """
    # URL-decode characters like %28, %29, etc.
    decoded_filename = unquote(filename)
    # Replace any character that is not a letter, number, dot, or underscore with a hyphen
    sanitized = re.sub(r'[^\w._-]', '-', decoded_filename)
    # Replace multiple consecutive hyphens with a single one
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading or trailing hyphens
    sanitized = sanitized.strip('-')
    return sanitized

def clean_html(soup, is_main_page=False):
    """
    Removes unwanted elements from a BeautifulSoup object, tailored for the Cerner Wiki site.

    Args:
        soup (BeautifulSoup): The parsed HTML object.
        is_main_page (bool): Flag to indicate if the page being cleaned is the main index page.
    """
    # Remove elements by their ID
    ids_to_remove = [
        'header',               # Main header banner
        'header-precursor',
        'main-header',
        'labels-section',
        'comments-section',
        'footer',
        'dbContext-wrapper',    # "This page is part of a Book" banner
        'space-tools-web-items' # "Overview, Content Tools, Tasks" footer
    ]
    for element_id in ids_to_remove:
        element = soup.find(id=element_id)
        if element:
            element.decompose()

    # Remove elements by their class name
    classes_to_remove = [
        'ia-splitter-left',    # Left sidebar
        'dbNav',               # DocBuilder navigation
        'page-metadata',       # "Last modified on..."
        'published-version'    # "The version of this page..." banner
    ]
    for class_name in classes_to_remove:
        for element in soup.find_all(class_=class_name):
            element.decompose()

    # --- NEW: Remove the hidden parameter fieldsets ---
    # This specifically targets the unwanted boxes you mentioned.
    for fieldset in soup.find_all('fieldset', class_='parameters hidden'):
        fieldset.decompose()

    # Remove all <section> tags, which are used for pop-up dialogs
    for section in soup.find_all('section'):
        section.decompose()

    # Remove all script, link, and meta tags to prevent external requests and clean up the head
    for s in soup.select('script, link, meta'):
        s.decompose()
        
    # Adjust the main content margin now that the sidebar is gone
    main_content = soup.find('main', id='main')
    if main_content:
        main_content.attrs.pop('style', None)

    # Remove the borders from the code example boxes
    for preformatted_box in soup.find_all('div', class_='preformatted'):
        preformatted_box.attrs.pop('style', None)

    # For the individual function pages (not the main index), remove all links within the content
    if not is_main_page:
        content_div = soup.find('div', id='main-content')
        if content_div:
            for a in content_div.find_all('a'):
                # Replace the <a> tag with its text content
                a.unwrap()

    return soup

def scrape_website(start_url, output_dir):
    """
    Scrapes a website, starting from a main page, downloading linked pages,
    cleaning them, and saving them for offline use.

    Args:
        start_url (str): The URL of the main page to start from.
        output_dir (str): The directory to save the cleaned HTML files.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': start_url
    }
    session.headers.update(headers)

    try:
        print(f"Fetching main page: {start_url}")
        response = session.get(start_url)
        response.raise_for_status()
        
        main_soup = BeautifulSoup(response.text, 'html.parser')

        # --- MODIFIED: Find all link containers, not just the first one ---
        link_containers = main_soup.find_all('div', class_='panelContent')
        if not link_containers:
            print("Error: Could not find any link container divs with class 'panelContent'.")
            return

        # --- MODIFIED: Collect links from all found containers ---
        links = []
        for container in link_containers:
            links.extend(container.find_all('a', href=True))
        
        print(f"Found {len(links)} function links to process.")

        for i, link in enumerate(links):
            time.sleep(1)
            href = link['href']
            absolute_url = urljoin(start_url, href)
            
            if urlparse(absolute_url).netloc != urlparse(start_url).netloc:
                print(f"  - Skipping external link: {absolute_url}")
                continue

            try:
                print(f"  ({i+1}/{len(links)}) Fetching function page: {absolute_url}")
                session.headers.update({'Referer': start_url})
                page_response = session.get(absolute_url)
                page_response.raise_for_status()
                
                page_soup = BeautifulSoup(page_response.text, 'html.parser')
                # Pass is_main_page=False to trigger link removal
                cleaned_page_soup = clean_html(page_soup, is_main_page=False)
                
                # --- NEW: Sanitize the filename before saving ---
                path_part = os.path.basename(urlparse(absolute_url).path)
                filename = sanitize_filename(path_part) + ".html"
                file_path = os.path.join(output_dir, filename)
                
                print(f"    - Saving to: {filename}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(cleaned_page_soup))
                
                # Update the link in the main index to point to the new local file
                link['href'] = filename
                
            except requests.exceptions.RequestException as e:
                print(f"    - ERROR fetching {absolute_url}: {e}")
                link['href'] = '#'
                link.string = f"[DOWNLOAD FAILED] {link.string}"

        # Clean the main page itself, keeping its links intact
        cleaned_main_soup = clean_html(main_soup, is_main_page=True)
        
        main_page_path = os.path.join(output_dir, "index.html")
        with open(main_page_path, 'w', encoding='utf-8') as f:
            f.write(str(cleaned_main_soup))
        print(f"\nScraping complete. Main page saved to: {main_page_path}")

    except requests.exceptions.RequestException as e:
        print(f"FATAL ERROR: Could not fetch the main URL {start_url}. {e}")

# --- Execution ---
URL_TO_SCRAPE = "https://wiki.cerner.com/display/public/1101discernHP/Functions+Reference+Help+in+Discern+Explorer"
OUTPUT_DIRECTORY = "ccl_functions"

if os.path.exists(OUTPUT_DIRECTORY):
    print(f"Removing old directory: {OUTPUT_DIRECTORY}")
    shutil.rmtree(OUTPUT_DIRECTORY)

scrape_website(URL_TO_SCRAPE, OUTPUT_DIRECTORY)

print(f"\nAll files have been saved in the '{OUTPUT_DIRECTORY}' directory.")
