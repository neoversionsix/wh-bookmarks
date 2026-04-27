import os

with open('c:/Users/whittlj2/Desktop/glossary.txt', encoding='utf-8') as f:
    glossary = f.read()

with open('c:/Users/whittlj2/Desktop/config_table.html', encoding='utf-8') as f:
    table = f.read()

html_template = """<!DOCTYPE html>
<html>
<head>
  <title>{title}</title>
  <link rel="icon" type="image/x-icon" href="../favicon.ico">
  <style>
    body {{ background-color: #222; color: #fff; font-family: sans-serif; padding: 20px; }}
    a {{ color: #ee8383; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
    th, td {{ border: 1px solid #555; padding: 8px; text-align: left; }}
    th {{ background-color: #444; position: sticky; top: 0; }}
    input.column-filter {{ width: 90%; padding: 4px; margin-top: 4px; box-sizing: border-box; background-color: #333; color: white; border: 1px solid #777; }}
    button {{
      background-color: #000000;
      color: #ffffff;
      border: 1px solid #ee8383;
      padding: 5px 10px;
      cursor: pointer;
      box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
      transition: all 0.3s ease;
      border-radius: 5px;
      font-size: 16px;
    }}
    button:hover {{
      background-color: #1a1a1a;
      box-shadow: 0 5px 15px rgba(238, 131, 131, 0.5);
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <a href='../index.html'><button>Back to Bookmarks</button></a>
  <br><br>
  {content}
  {script}
</body>
</html>"""

js_script = """
<script>
  document.addEventListener('DOMContentLoaded', function() {
    const table = document.querySelector('table');
    if (!table) return;
    
    // Create filter row
    const thead = table.querySelector('thead');
    const headerRow = thead.querySelector('tr');
    const filterRow = document.createElement('tr');
    
    const headers = Array.from(headerRow.querySelectorAll('th'));
    const inputs = [];
    
    headers.forEach((th, index) => {
      const td = document.createElement('th');
      const input = document.createElement('input');
      input.type = 'text';
      input.placeholder = 'Filter...';
      input.className = 'column-filter';
      
      // Filter logic
      input.addEventListener('input', function() {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.forEach(row => {
          let show = true;
          const cells = Array.from(row.querySelectorAll('td, th'));
          
          inputs.forEach((inp, idx) => {
            const filterText = inp.value.toLowerCase();
            if (filterText) {
              const cellText = cells[idx] ? cells[idx].textContent.toLowerCase() : '';
              if (!cellText.includes(filterText)) {
                show = false;
              }
            }
          });
          
          row.style.display = show ? '' : 'none';
        });
      });
      
      inputs.push(input);
      td.appendChild(input);
      filterRow.appendChild(td);
    });
    
    thead.appendChild(filterRow);
  });
</script>
"""

with open('c:/Users/whittlj2/GitHub/wh-bookmarks/pages/hdi-config-glossary.html', 'w', encoding='utf-8') as f:
    f.write(html_template.format(title='MD REF Config File Glossary', content=glossary, script=''))

with open('c:/Users/whittlj2/GitHub/wh-bookmarks/pages/hdi-config-variables.html', 'w', encoding='utf-8') as f:
    table = table.replace('style="width: 87.5268%;"', '')
    f.write(html_template.format(title='MD REF Config Variables Table', content=table, script=js_script))
