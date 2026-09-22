# -*- coding: utf-8 -*-
import os, sys, json, re, zipfile, io
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
    CREDS_FILE, scopes=[
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
)
service = build('sheets', 'v4', credentials=creds)
drive_service = build('drive', 'v3', credentials=creds)

def extract_in_cell_images():
    print("  🖼️ Checking for in-cell images directly from Google Sheets...")
    dest_dir = os.path.join(os.path.dirname(__file__), 'images')
    os.makedirs(dest_dir, exist_ok=True)
    extracted_map = {}
    try:
        req = drive_service.files().export_media(
            fileId=PRIVATE_SID,
            mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        xlsx_bytes = req.execute()
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(io.BytesIO(xlsx_bytes)) as z:
            wb_xml = z.read('xl/workbook.xml').decode('utf-8')
            root = ET.fromstring(wb_xml)
            sheets_map = {}
            for elem in root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet'):
                name = elem.attrib['name']
                r_id = elem.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
                sheets_map[r_id] = name

            wb_rels = z.read('xl/_rels/workbook.xml.rels').decode('utf-8')
            rels_root = ET.fromstring(wb_rels)
            sheet_files_map = {}
            for elem in rels_root.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                r_id = elem.attrib['Id']
                target = elem.attrib['Target']
                if r_id in sheets_map:
                    sheet_files_map[target] = sheets_map[r_id]

            drawing_to_sheet = {}
            for name in z.namelist():
                if name.startswith('xl/worksheets/_rels/'):
                    sheet_xml = 'worksheets/' + name.replace('xl/worksheets/_rels/', '').replace('.rels', '')
                    sheet_name = sheet_files_map.get(sheet_xml)
                    if not sheet_name: continue
                    rels_content = z.read(name).decode('utf-8')
                    r_elem = ET.fromstring(rels_content)
                    for rel in r_elem.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                        target = rel.attrib.get('Target', '')
                        if 'drawing' in target:
                            d_name = os.path.basename(target)
                            drawing_to_sheet[d_name] = sheet_name

            for d_name, sheet_name in drawing_to_sheet.items():
                d_path = f'xl/drawings/{d_name}'
                d_rels_path = f'xl/drawings/_rels/{d_name}.rels'
                if d_path not in z.namelist() or d_rels_path not in z.namelist():
                    continue

                d_rels_content = z.read(d_rels_path).decode('utf-8')
                d_rels_root = ET.fromstring(d_rels_content)
                media_map = {}
                for rel in d_rels_root.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                    r_id = rel.attrib['Id']
                    target = rel.attrib['Target']
                    media_file = 'xl/' + target.replace('../', '')
                    media_map[r_id] = media_file

                d_xml = z.read(d_path).decode('utf-8')
                d_root = ET.fromstring(d_xml)

                for anchor in d_root:
                    from_elem = anchor.find('{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}from')
                    if from_elem is None: continue
                    col_elem = from_elem.find('{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}col')
                    row_elem = from_elem.find('{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}row')
                    if col_elem is None or row_elem is None: continue

                    col_idx = int(col_elem.text)
                    row_idx = int(row_elem.text) + 1

                    blip = anchor.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
                    if blip is None: continue
                    embed_id = blip.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    if not embed_id or embed_id not in media_map: continue

                    media_file = media_map[embed_id]
                    if media_file in z.namelist():
                        ext = os.path.splitext(media_file)[1]
                        clean_sheet = re.sub(r'[^a-zA-Z0-9_]', '_', sheet_name)
                        out_fname = f"extracted_{clean_sheet}_r{row_idx}_c{col_idx}{ext}"
                        out_path = os.path.join(dest_dir, out_fname)
                        with open(out_path, 'wb') as out_f:
                            out_f.write(z.read(media_file))
                        rel_path = f"images/{out_fname}"
                        extracted_map[(sheet_name, row_idx, col_idx)] = rel_path
                        print(f"     Found in-cell image: [{sheet_name}] Row {row_idx} Col {col_idx} -> {rel_path}")

        print(f"  ✅ Extracted {len(extracted_map)} in-cell images from Google Sheets successfully.")
    except Exception as e:
        print(f"  ⚠️ In-cell image extraction warning: {e}")
    return extracted_map

in_cell_images_map = extract_in_cell_images()

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
    ranges=[f"{t}!A1:H2000" for t in all_tab_names],
    includeGridData=True
).execute()

sheets_dict = {s['properties']['title']: s for s in sheet_meta.get('sheets', [])}
print(f"Loaded {len(sheets_dict)} total sheets with full ranges from Google Sheets.")

def escape_html(s):
    if not s:
        return ""
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#039;')

def apply_clinical_highlighting(text):
    if not text:
        return ""
    
    # 1. First escape HTML
    escaped = escape_html(text)

    # 2. Header Badges & Callout Formatting
    escaped = re.sub(
        r'▶\s*\[(ข้อสอบจริง\s*/\s*Real Exam Question|ข้อสอบจริง|Real Exam Question)\]:?',
        r'<div style="display:inline-flex; align-items:center; gap:5px; background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; padding:3px 10px; border-radius:6px; font-weight:700; font-size:0.88em; margin-bottom:8px; box-shadow:0 1px 2px rgba(0,0,0,0.05);">🎯 ข้อสอบจริง / Real Exam</div><br>',
        escaped
    )
    escaped = re.sub(
        r'▶\s*\[(Clinical Case Scenario|Clinical Case)\]:?|Case\s*\[(Easy|Hard|Medium)[^\]]*\]:?',
        r'<div style="display:inline-flex; align-items:center; gap:5px; background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; padding:3px 10px; border-radius:6px; font-weight:700; font-size:0.88em; margin-bottom:8px; box-shadow:0 1px 2px rgba(0,0,0,0.05);">📋 Clinical Case Scenario</div><br>',
        escaped
    )
    escaped = re.sub(
        r'▶\s*\[(เฉลย)\]:?',
        r'<div style="display:inline-flex; align-items:center; gap:5px; background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; padding:2px 8px; border-radius:5px; font-weight:700; font-size:0.9em; margin-bottom:6px;">✅ เฉลย:</div>',
        escaped
    )
    escaped = re.sub(
        r'💡\s*\[(คำอธิบายและจุดเน้นข้อสอบ|คำอธิบาย[^\]]*)\]:?',
        r'<div style="background:#fffbeb; color:#92400e; border-left:3px solid #f59e0b; padding:6px 12px; border-radius:0 6px 6px 0; font-weight:600; margin:10px 0;">💡 คำอธิบายและจุดเน้นข้อสอบ:</div>',
        escaped
    )
    escaped = re.sub(
        r'▶\s*\[([^\]]+)\]:?',
        r'<div style="color:#0f172a; font-weight:700; font-size:0.95em; margin:8px 0 4px 0; border-bottom:1px dashed #cbd5e1; padding-bottom:2px;">▶ \1</div>',
        escaped
    )
    escaped = re.sub(
        r'(?m)^([ก-ง]\.)\s+',
        r'<div style="margin:4px 0 4px 8px;"><b style="color:#1e293b; background:#f1f5f9; padding:1px 6px; border-radius:4px; margin-right:4px;">\1</b> ',
        escaped
    )
    escaped = re.sub(
        r'↳\s+',
        r'<span style="color:#64748b; font-weight:bold; margin-right:4px;">↳</span>',
        escaped
    )

    # 3. 5-Color Clinical Palette
    C_GREEN  = '#16a34a' # DOC & Regimens
    C_RED    = '#dc2626' # Warnings, Contraindications, Severe ADRs
    C_AMBER  = '#d97706' # Criteria, Scores, Cutoffs
    C_PURPLE = '#7c3aed' # Pathogens, Resistance Genes, Enzymes
    C_BLUE   = '#0284c7' # Drug Names & Classes

    reg_purple_species = [
        r'Streptococcus pneumoniae', r'S\.\s*pneumoniae', r'Streptococcus pyogenes', r'S\.\s*pyogenes',
        r'Staphylococcus aureus', r'S\.\s*aureus',
        r'Enterococcus faecalis', r'E\.\s*faecalis', r'Enterococcus faecium', r'E\.\s*faecium',
        r'Pseudomonas aeruginosa', r'P\.\s*aeruginosa', r'Acinetobacter baumannii', r'A\.\s*baumannii',
        r'Klebsiella pneumoniae', r'K\.\s*pneumoniae', r'Escherichia coli', r'E\.\s*coli',
        r'Neisseria meningitidis', r'N\.\s*meningitidis', r'Neisseria gonorrhoeae', r'N\.\s*gonorrhoeae',
        r'Listeria monocytogenes', r'L\.\s*monocytogenes', r'Haemophilus influenzae', r'H\.\s*influenzae',
        r'Mycobacterium tuberculosis', r'M\.\s*tuberculosis', r'Mycobacterium bovis', r'M\.\s*bovis',
        r'Pasteurella multocida', r'Pasteurella spp\.', r'Pasteurella',
        r'Eikenella corrodens', r'Eikenella spp\.', r'Eikenella',
        r'Viridans Streptococci', r'Viridans Group Streptococci', r'Viridans strep',
        r'Streptococcus gallolyticus', r'Streptococcus bovis', r'S\.\s*bovis'
    ]

    reg_purple_genes = [
        r'MDR-TB', r'Pre-XDR-TB', r'Pre-XDR', r'XDR-TB', r'RR-TB',
        r'MSSA', r'MRSA', r'VISA', r'VRSA', r'VRE', r'ESBL', r'AmpC', r'CRE', r'CRAB', r'CRPA',
        r'mecA', r'PBP2a', r'PBP', r'vanA', r'vanB', r'blaCTX-M', r'blaSHV', r'blaTEM',
        r'blaKPC', r'blaNDM', r'blaOXA', r'katG', r'inhA', r'rpoB', r'pncA', r'embB',
        r'atpE', r'gyrA', r'gyrB', r'rrs', r'23S rRNA', r'OprD', r'MexAB-OprM', r'Efflux pumps?',
        r'DNA Gyrase', r'Topoisomerase IV', r'ATP Synthase', r'RNA Polymerase'
    ]

    reg_green = [
        r'Drug of Choice', r'First-line DOC', r'First-line', r'DOC',
        r'ยาขนานแรก', r'ยาทางเลือกอันดับ 1', r'ยาหลัก', r'สูตรมาตรฐาน',
        r'BPaLM Regimen', r'BPaLM', r'BPaL Regimen', r'BPaL',
        r'2HRZE\s*/\s*4HR', r'2HRZE', r'4HR', r'6\s*R-Z-E-Lfx',
        r'Empirical therapy', r'Empiric therapy', r'Empiric DOC'
    ]

    reg_red = [
        r'QT Prolongation', r'QTc\s*>\s*500\s*ms', r'Torsades de Pointes', r'TdP',
        r'TB-DILI', r'DILI', r'ตับอักเสบรุนแรง', r'ตับวาย', r'มะเร็งตับวาย',
        r'Myelosuppression', r'กดไขกระดูก', r'Aplastic anemia', r'Thrombocytopenia',
        r'เกล็ดเลือดต่ำ', r'เม็ดเลือดขาวต่ำ', r'Optic Neuropathy', r'ตาบอดสีแดง-เขียว',
        r'Peripheral Neuropathy', r'ปลายประสาทอักเสบ', r'Ototoxicity', r'พิษต่อหู',
        r'Nephrotoxicity', r'พิษต่อไต', r'ไตวายเฉียบพลัน', r'Red Man Syndrome',
        r'Hypothyroidism', r'ภาวะไทรอยด์ทำงานต่ำ', r'Psychosis', r'อาการทางจิตเวช',
        r'Suicidal ideation', r'Seizure', r'ชัก', r'ห้ามใช้เด็ดขาด', r'ข้อห้ามใช้เด็ดขาด',
        r'ข้อห้ามใช้', r'Contraindicated', r'ห้ามใช้', r'อันตราย', r'Dead Zone'
    ]

    reg_amber = [
        r'Modified Duke Criteria', r'Duke Criteria', r'Definite IE', r'Possible IE',
        r'Major criteria', r'Minor criteria', r'Major Criteria', r'Minor Criteria',
        r'CURB-65\s*>=\s*[0-9]', r'CURB-65', r'CURB65', r'PEDIS Grade\s*[0-9]',
        r'PEDIS Grade', r'CrCl\s*<\s*30\s*mL/min', r'CrCl\s*<\s*50\s*mL/min',
        r'CrCl\s*<\s*[0-9]+', r'ALT\s*>\s*3x\s*ULN', r'ALT\s*>\s*5x\s*ULN',
        r'Total Bilirubin\s*>\s*2\.0\s*mg/dL', r'Hb\s*<\s*8(\.0)?\s*g/dL',
        r'Platelets\s*<\s*50,000\s*/mcL', r'PMN\s*>\s*75%', r'CSF opening pressure',
        r'GeneXpert MTB/RIF', r'GeneXpert', r'Line Probe Assay', r'LPA'
    ]

    reg_blue = [
        r'Penicillin G', r'Penicillin', r'Ampicillin', r'Amoxicillin-Clavulanate', r'Amoxicillin/Clavulanate',
        r'Amoxicillin', r'Augmentin', r'Cloxacillin', r'Oxacillin', r'Nafcillin', r'Dicloxacillin',
        r'Cefazolin', r'Cephalexin', r'Cefalexin', r'Ceftriaxone', r'Ceftazidime/Avibactam',
        r'Ceftazidime', r'Cefepime', r'Ceftaroline', r'Meropenem', r'Imipenem', r'Ertapenem', r'Doripenem',
        r'Piperacillin/Tazobactam', r'Piperacillin', r'Tazobactam', r'Sulbactam', r'Clavulanate',
        r'Vancomycin', r'Daptomycin', r'Linezolid', r'Tedizolid', r'Colistin', r'Polymyxin B',
        r'Fosfomycin', r'Gentamicin', r'Amikacin', r'Tobramycin', r'Streptomycin', r'Kanamycin',
        r'Ciprofloxacin', r'Levofloxacin', r'Moxifloxacin', r'Azithromycin', r'Clarithromycin',
        r'Erythromycin', r'Doxycycline', r'Minocycline', r'Tigecycline', r'Cotrimoxazole',
        r'TMP/SMX', r'Metronidazole', r'Clindamycin', r'Rifampin', r'Rifampicin', r'Isoniazid',
        r'Pyrazinamide', r'Ethambutol', r'Bedaquiline', r'Pretomanid', r'Delamanid', r'Clofazimine',
        r'Cycloserine', r'Ethionamide', r'Prothionamide', r'Pyridoxine', r'Vitamin B6',
        r'Levothyroxine', r'Dexamethasone', r'Remdesivir', r'Molnupiravir', r'Paxlovid', r'Favipiravir'
    ]

    placeholders = {}
    counter = [0]
    def make_span(m, color, is_italic=False):
        val = m.group(0)
        idx = counter[0]
        counter[0] += 1
        key = f"___HL_SPAN_{idx}___"
        inner = f"<i>{val}</i>" if is_italic else val
        placeholders[key] = f'<b style="color:{color};">{inner}</b>'
        return key

    order = [
        (C_GREEN, reg_green, False),
        (C_RED, reg_red, False),
        (C_AMBER, reg_amber, False),
        (C_PURPLE, reg_purple_species, True), # Species are Italic + Bold Purple
        (C_PURPLE, reg_purple_genes, False),
        (C_BLUE, reg_blue, False)
    ]

    current_text = escaped
    for color, pat_list, is_it in order:
        sorted_pats = sorted(pat_list, key=len, reverse=True)
        combined_regex = r'(?<![a-zA-Z0-9_\u0E00-\u0E7F])(' + '|'.join(sorted_pats) + r')(?![a-zA-Z0-9_\u0E00-\u0E7F])'
        current_text = re.sub(combined_regex, lambda m, c=color, it=is_it: make_span(m, c, it), current_text, flags=re.IGNORECASE)

    for key, span_html in placeholders.items():
        current_text = current_text.replace(key, span_html)

    return current_text.replace('\n', '<br>')

def rich_text_to_html(cell):
    text = cell.get('formattedValue') or cell.get('userEnteredValue', {}).get('stringValue', '')
    if not text:
        return ""
    
    runs = cell.get('textFormatRuns')
    if not runs:
        return apply_clinical_highlighting(text)

    # Check if runs contain actual colors
    has_color_run = False
    for r in runs:
        if r.get('format', {}).get('foregroundColor'):
            has_color_run = True
            break
    if not has_color_run:
        return apply_clinical_highlighting(text)

    sorted_runs = sorted(runs, key=lambda r: r.get('startIndex', 0))
    if sorted_runs and sorted_runs[0].get('startIndex', 0) > 0:
        sorted_runs.insert(0, {'startIndex': 0, 'format': {}})
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
                    formula = c.get('userEnteredValue', {}).get('formulaValue', '')
                    if formula and 'IMAGE' in formula.upper():
                        m = re.search(r'["\']([^"\']+)["\']', formula)
                        if m:
                            return m.group(1)
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

            q_img_final = to_direct_image_url(q_url)
            if not q_img_final:
                q_img_final = in_cell_images_map.get((title, r_idx + 1, 2), "")

            a_img_final = to_direct_image_url(a_url)
            if not a_img_final:
                a_img_final = in_cell_images_map.get((title, r_idx + 1, 4), "")

            card_obj = {
                "id": f"{title}::{r_idx + 1}",
                "itemNo": colA if colA else str(len(cards_in_tab) + 1),
                "group": title,
                "subTopic": subtopic if subtopic else title,
                "track": track,
                "question": q_html,
                "questionImage": q_img_final,
                "answer": a_html,
                "answerImage": a_img_final,
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
