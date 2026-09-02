# -*- coding: utf-8 -*-
import os, sys, json, re
from google.oauth2 import service_account
from googleapiclient.discovery import build

sys.stdout.reconfigure(encoding='utf-8')

CREDS_FILE = 'C:/Users/thana/Desktop/PLE-CC/gemini-sheets-editor-497118-060a7f15daf9.json'
PRIVATE_SID = '1U9JfDwzg-UthEBSjdZBy0p0Y_MaNojZm6nYo74IO5Fg'
OUTPUT_JS = os.path.join(os.path.dirname(__file__), 'flashcard-data-offline.js')

print("=" * 60)
print("  🚀 PharmaCU Flashcard Private -- Offline DB Compiler")
print(f"  Target Sheet: {PRIVATE_SID}")
print("=" * 60)

creds = service_account.Credentials.from_service_account_file(
    CREDS_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
service = build('sheets', 'v4', credentials=creds)

# 1. Fetch metadata
sheet_meta = service.spreadsheets().get(
    spreadsheetId=PRIVATE_SID,
    includeGridData=True
).execute()

sheets = sheet_meta.get('sheets', [])
print(f"Found {len(sheets)} tabs in spreadsheet.")

def escape_html(s):
    if not s:
        return ""
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def format_rich_cell(cell):
    text = cell.get('formattedValue') or cell.get('userEnteredValue', {}).get('stringValue', '')
    if not text:
        return ""
    
    runs = cell.get('textFormatRuns')
    if not runs:
        # If no explicit runs, format by hierarchy symbols
        html_lines = []
        for line in text.split('\n'):
            escaped = escape_html(line)
            if escaped.startswith('▶'):
                html_lines.append(f'<div class="card-h1">{escaped}</div>')
            elif escaped.strip().startswith('↳'):
                html_lines.append(f'<div class="card-item">{escaped}</div>')
            elif escaped.strip().startswith('✦'):
                html_lines.append(f'<div class="card-warn">{escaped}</div>')
            elif escaped.strip().startswith('•'):
                html_lines.append(f'<div class="card-bullet">{escaped}</div>')
            else:
                html_lines.append(f'<div class="card-p">{escaped}</div>')
        return "".join(html_lines)

    # Sort runs by startIndex
    sorted_runs = sorted(runs, key=lambda r: r.get('startIndex', 0))
    # Build text segments using UTF-16 decoding
    encoded_u16 = text.encode('utf-16-le')
    total_u16_len = len(encoded_u16) // 2

    html_parts = []
    prev_idx = 0

    for i, r in enumerate(sorted_runs):
        start = r.get('startIndex', 0)
        end = sorted_runs[i + 1].get('startIndex', total_u16_len) if (i + 1 < len(sorted_runs)) else total_u16_len
        
        # slice utf-16 bytes
        seg_bytes = encoded_u16[start * 2 : end * 2]
        seg_text = seg_bytes.decode('utf-16-le', errors='ignore')
        
        # determine styles
        fmt = r.get('format', {})
        fg = fmt.get('foregroundColor', {})
        bold = fmt.get('bold', False)
        
        styles = []
        if bold:
            styles.append("font-weight: 700;")
        
        if fg:
            red = fg.get('red', 0)
            green = fg.get('green', 0)
            blue = fg.get('blue', 0)
            # Detect PharmaCU palette colors
            # Blue: red ~0, green ~0.5, blue ~0.78
            if blue > 0.6 and red < 0.2:
                styles.append("color: #0284c7; font-weight: 700;")
            # Green: green > 0.5, red < 0.3
            elif green > 0.5 and red < 0.3:
                styles.append("color: #16a34a; font-weight: 700;")
            # Red: red > 0.7, green < 0.3
            elif red > 0.7 and green < 0.3:
                styles.append("color: #dc2626; font-weight: 700;")
            # Purple: red ~0.48, blue ~0.9
            elif blue > 0.6 and red > 0.3:
                styles.append("color: #7c3aed; font-weight: 700;")
            # Amber: red ~0.8, green ~0.4, blue < 0.2
            elif red > 0.7 and green > 0.3 and blue < 0.2:
                styles.append("color: #d97706; font-weight: 700;")
            elif not (red == 0 and green == 0 and blue == 0):
                r_int = int(round(red * 255))
                g_int = int(round(green * 255))
                b_int = int(round(blue * 255))
                styles.append(f"color: rgb({r_int},{g_int},{b_int});")

        escaped_seg = escape_html(seg_text)
        if styles:
            style_str = " ".join(styles)
            html_parts.append(f'<span style="{style_str}">{escaped_seg}</span>')
        else:
            html_parts.append(escaped_seg)

    full_html = "".join(html_parts)
    # Convert newlines to formatted lines
    final_lines = []
    for line in full_html.split('\n'):
        line_clean = line.strip()
        if not line_clean:
            final_lines.append('<div class="spacer"></div>')
        elif line_clean.startswith('▶'):
            final_lines.append(f'<div class="card-h1">{line}</div>')
        elif line_clean.startswith('↳') or '↳' in line_clean[:6]:
            final_lines.append(f'<div class="card-item">{line}</div>')
        elif line_clean.startswith('✦') or '✦' in line_clean[:6]:
            final_lines.append(f'<div class="card-warn">{line}</div>')
        elif line_clean.startswith('•') or '•' in line_clean[:6]:
            final_lines.append(f'<div class="card-bullet">{line}</div>')
        else:
            final_lines.append(f'<div class="card-p">{line}</div>')
            
    return "".join(final_lines)

all_tabs_data = []
total_compiled_cards = 0

for sheet in sheets:
    props = sheet['properties']
    title = props['title']
    sheet_id = props['sheetId']
    
    # Skip system tabs
    if title in ['สารบัญ', 'Users', 'Sessions', 'History']:
        continue
        
    data = sheet.get('data', [])
    if not data:
        continue
        
    row_data = data[0].get('rowMetadata', [])
    rows = data[0].get('rowData', [])
    
    if len(rows) <= 2:
        continue
        
    print(f"--> Processing Tab: '{title}' ({len(rows) - 2} potential rows)...")
    
    tab_cards = []
    # Start from row 3 (index 2)
    for r_idx in range(2, len(rows)):
        row = rows[r_idx]
        cells = row.get('values', [])
        if not cells:
            continue
            
        def get_val(idx):
            if idx < len(cells):
                c = cells[idx]
                return c.get('formattedValue') or c.get('userEnteredValue', {}).get('stringValue') or str(c.get('userEnteredValue', {}).get('numberValue', ''))
            return ""

        cid = get_val(0).strip()
        q = get_val(1).strip()
        q_url = get_val(2).strip()
        a_cell = cells[3] if len(cells) > 3 else {}
        a_text = get_val(3).strip()
        a_url = get_val(4).strip()
        subtopic = get_val(5).strip()
        note = get_val(6).strip()
        
        if not q and not a_text:
            continue
            
        # Parse RichText HTML for answer
        a_html = format_rich_cell(a_cell)
        
        # Canonicalize ID
        card_id = cid if cid else str(len(tab_cards) + 1)
        
        tab_cards.append({
            "id": card_id,
            "tab": title,
            "question": q,
            "q_url": q_url,
            "answer_raw": a_text,
            "answer_html": a_html,
            "a_url": a_url,
            "subtopic": subtopic if subtopic else title,
            "note": note
        })
        
    if tab_cards:
        total_compiled_cards += len(tab_cards)
        all_tabs_data.append({
            "title": title,
            "sheet_id": sheet_id,
            "count": len(tab_cards),
            "cards": tab_cards
        })
        print(f"    ✅ Extracted {len(tab_cards)} valid flashcards from '{title}'")

print("-" * 60)
print(f"Total compiled flashcards: {total_compiled_cards} across {len(all_tabs_data)} tabs.")

# Generate offline JS file
db_payload = {
    "generated_at": str(os.popen('date /T').read()).strip() + " " + str(os.popen('time /T').read()).strip(),
    "total_cards": total_compiled_cards,
    "tabs": all_tabs_data
}

js_content = "/**\n * PharmaCU Flashcard Private -- Pre-compiled Offline Database\n * Auto-generated from Google Sheets: " + PRIVATE_SID + "\n */\n"
js_content += "window.FLASHCARD_DATABASE = " + json.dumps(db_payload, ensure_ascii=False, indent=2) + ";\n"

with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f"🎉 Successfully written offline database to: {OUTPUT_JS}")
print(f"   File size: {os.path.getsize(OUTPUT_JS):,} bytes")
print("=" * 60)
