# -*- coding: utf-8 -*-
import os, sys, json, re
from google.oauth2 import service_account
from googleapiclient.discovery import build

sys.stdout.reconfigure(encoding='utf-8')

CREDS_FILE = 'C:/Users/thana/Desktop/PLE-CC/gemini-sheets-editor-497118-060a7f15daf9.json'
PRIVATE_SID = '1U9JfDwzg-UthEBSjdZBy0p0Y_MaNojZm6nYo74IO5Fg'
OUTPUT_JS = os.path.join(os.path.dirname(__file__), 'flashcard-data-offline.js')

print("=" * 65)
print("  🚀 PharmaCU Flashcard Private -- Complete 16 Clinic + 12 Product Compiler")
print(f"  Target Sheet: {PRIVATE_SID}")
print("=" * 65)

creds = service_account.Credentials.from_service_account_file(
    CREDS_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
service = build('sheets', 'v4', credentials=creds)

CLINIC_TAB_NAMES = [
  "1. Musculoskeleton", "2. Cardiovascular", "3. Dermatologic", "4. Endocrine",
  "5. Gastrointestinal", "6. Hematologic", "7. Immunologic", "8. Infectious diseases",
  "9. Neurologic", "10. Psychiatric", "11. Pulmonary", "12. Gynaecologic/Genitourinary",
  "13. Eye disorder", "14. Oncologic", "15. Renal", "16. Others & Toxic"
]

PRODUCT_TAB_NAMES = [
  "1. Titrations", "2. Chromatography", "3. Spectroscopy & Optics", "4. Preformulation & GMP",
  "5. Pharmaceutical Calc", "6. Solid Dosage Forms", "7. Liquid & Semisolids",
  "8. Biopharm & Drug Release", "9. Sterile & Special Forms", "10. Biotech Products",
  "11. Herbal Products", "12. Food Products & QA"
]

all_tab_names = CLINIC_TAB_NAMES + PRODUCT_TAB_NAMES
sheet_meta = service.spreadsheets().get(
    spreadsheetId=PRIVATE_SID,
    ranges=[f"{t}!A1:H500" for t in all_tab_names],
    includeGridData=True
).execute()

sheets_dict = {s['properties']['title']: s for s in sheet_meta.get('sheets', [])}
print(f"Loaded {len(sheets_dict)} total sheets with full ranges from Google Sheets.")

def escape_html(s):
    if not s:
        return ""
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#039;')

def rich_text_to_html(cell):
    text = cell.get('formattedValue') or cell.get('userEnteredValue', {}).get('stringValue', '')
    if not text:
        return ""
    
    runs = cell.get('textFormatRuns')
    if not runs:
        escaped = escape_html(text)
        return escaped.replace('\n', '<br>')

    sorted_runs = sorted(runs, key=lambda r: r.get('startIndex', 0))
    encoded_u16 = text.encode('utf-16-le')
    total_u16_len = len(encoded_u16) // 2

    html_parts = []
    for i, r in enumerate(sorted_runs):
        start = r.get('startIndex', 0)
        end = sorted_runs[i + 1].get('startIndex', total_u16_len) if (i + 1 < len(sorted_runs)) else total_u16_len
        
        seg_bytes = encoded_u16[start * 2 : end * 2]
        seg_text = seg_bytes.decode('utf-16-le', errors='ignore')
        
        fmt = r.get('format', {})
        bold = fmt.get('bold', False)
        italic = fmt.get('italic', False)
        underline = fmt.get('underline', False)
        fg = fmt.get('foregroundColor', {})
        
        t = escape_html(seg_text)
        if not t:
            continue
        
        if bold:
            t = f'<b>{t}</b>'
        if italic:
            t = f'<i>{t}</i>'
        if underline:
            t = f'<u>{t}</u>'
            
        color_hex = None
        if fg:
            red = fg.get('red', 0)
            green = fg.get('green', 0)
            blue = fg.get('blue', 0)
            if blue > 0.6 and red < 0.2:
                color_hex = '#0284c7'
            elif green > 0.5 and red < 0.3:
                color_hex = '#16a34a'
            elif red > 0.7 and green < 0.3:
                color_hex = '#dc2626'
            elif blue > 0.6 and red > 0.3:
                color_hex = '#7c3aed'
            elif red > 0.7 and green > 0.3 and blue < 0.2:
                color_hex = '#d97706'
            elif not (red == 0 and green == 0 and blue == 0):
                r_int = int(round(red * 255))
                g_int = int(round(green * 255))
                b_int = int(round(blue * 255))
                color_hex = f'#{r_int:02x}{g_int:02x}{b_int:02x}'
                
        if color_hex and color_hex != '#000000':
            t = f'<span style="color:{color_hex}">{t}</span>'
            
        html_parts.append(t)
        
    full_html = "".join(html_parts)
    return full_html.replace('\n', '<br>')

categories_list = []
offline_cards_map = {}
offline_all_cards = {
    'clinic': [],
    'product': [],
    'sap': [],
    'all': []
}

total_cards = 0

all_ordered_tabs = [(t, 'Clinic') for t in CLINIC_TAB_NAMES] + [(t, 'Product') for t in PRODUCT_TAB_NAMES]

for title, track in all_ordered_tabs:
    sheet = sheets_dict.get(title)
    cards_in_tab = []
    subtopics_set = set()
    
    if sheet:
        data = sheet.get('data', [])
        rows = []
        for grid in data:
            rows.extend(grid.get('rowData', []))
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

            colA = get_val(0).strip()
            colB = get_val(1).strip()
            
            if 'กลับหน้าสารบัญ' in colA or colA == 'ข้อที่' or colB in ['Question', 'คำถาม', 'Question / คำถาม', 'คำถาม / Question']:
                continue
            if not colA and not colB:
                continue
                
            q_cell = cells[1] if len(cells) > 1 else {}
            q_url = get_val(2).strip()
            a_cell = cells[3] if len(cells) > 3 else {}
            a_url = get_val(4).strip()
            subtopic = get_val(5).strip()
            note = get_val(6).strip()
            
            q_html = rich_text_to_html(q_cell) or colB
            a_html = rich_text_to_html(a_cell) or get_val(3).strip()
            
            if subtopic:
                subtopics_set.add(subtopic)
                
            def to_direct_image_url(u):
                if not u: return ""
                u = u.strip()
                if u.startswith('images/') or u.startswith('./images/'): return u
                if not (u.startswith('http://') or u.startswith('https://')):
                    if u.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                        return f"images/{u}"
                    return ""
                m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', u)
                if not m:
                    m = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', u)
                if m:
                    return f"https://lh3.googleusercontent.com/d/{m.group(1)}"
                return u

            card_obj = {
                "id": f"{title}::{r_idx + 1}",
                "itemNo": colA if colA else str(len(cards_in_tab) + 1),
                "group": title,
                "subTopic": subtopic if subtopic else title,
                "track": track,
                "question": q_html,
                "questionImage": to_direct_image_url(q_url),
                "answer": a_html,
                "answerImage": to_direct_image_url(a_url),
                "note": note
            }
            
            cards_in_tab.append(card_obj)
            offline_all_cards[track.lower()].append(card_obj)
            offline_all_cards['all'].append(card_obj)

    total_cards += len(cards_in_tab)
    offline_cards_map[title] = cards_in_tab
    categories_list.append({
        "name": title,
        "track": track,
        "count": len(cards_in_tab),
        "subtopics": sorted(list(subtopics_set))
    })
    status_icon = "✅" if cards_in_tab else "⚪"
    print(f"  {status_icon} [{track:7}] {title:30}: {len(cards_in_tab):3} cards, {len(subtopics_set):2} subtopics")

print("-" * 65)
print(f"Total compiled cards: {total_cards} across {len(categories_list)} categories (16 Clinic + 12 Product).")

js_code = """/**
 * PharmaCU Flashcard Private -- Pre-compiled Offline Database
 * Compatible with original Index.html UI & Data structures
 */
window.OFFLINE_CATEGORIES = """ + json.dumps(categories_list, ensure_ascii=False, indent=2) + """;

window.OFFLINE_CARDS = """ + json.dumps(offline_cards_map, ensure_ascii=False, indent=2) + """;

window.OFFLINE_ALL_CARDS_BY_TRACK = """ + json.dumps(offline_all_cards, ensure_ascii=False, indent=2) + """;
"""

with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
    f.write(js_code)

print(f"🎉 Wrote offline database to: {OUTPUT_JS}")
print(f"   Size: {os.path.getsize(OUTPUT_JS):,} bytes")
print("=" * 65)
