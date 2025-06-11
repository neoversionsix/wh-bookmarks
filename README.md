# wh-bookmarks

A web-based bookmark site for Digital Health team members at Western Health.  
This site provides quick access to frequently used links, tools, documentation, and resources relevant to Cerner, Cherwell, HL7, Pharmacy, and other internal systems.

> **Note:**  
> This repository does **not** contain any sensitive or confidential data.  
> It only provides links to internal and external resources for convenience.

## Features

- **Searchable Bookmarks:** Quickly filter and find links using the search bar.
- **Environment Links:** Direct access to Cerner environments (PROD, CERT, BUILD, etc.).
- **Cherwell Integration:** Open incidents, problems, tasks, and knowledge articles in both browser and desktop app.
- **Documentation:** Links to OneNotes, SharePoint, and internal documentation.
- **Developed Tools:** Access to custom tools for PBS mapping, anomaly checking, code generation, and more.
- **Pharmacy & HL7 Resources:** Quick links to PBS, SNOMED, HL7 guides, and related resources.

## Structure

- `index.html` — Main bookmark page with categorized links and search.
- `tools/` — Custom web tools (PBS mapping, code generator, etc.).
- `documentation/` — Internal documentation and guides.
- `other/` — Legacy files and miscellaneous resources.

## Usage

1. Open `index.html` in your browser.
2. Use the search bar to filter links.
3. Click any button to open the corresponding resource in a new tab.

## Customization

- To add or update links, edit `index.html`.
- To add new tools, place HTML files in the `tools/` directory and link them from the main page.

## License

Internal use only.
