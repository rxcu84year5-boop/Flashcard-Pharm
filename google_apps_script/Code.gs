/**
 * =========================================================================
 * 🧬 PharmaCU Flashcard Private — Blazing Fast Live Web App API (Code.gs)
 * =========================================================================
 * ติดตั้งใน Google Sheet: Extensions (ส่วนขยาย) > Apps Script
 * =========================================================================
 */

function doGet(e) {
  try {
    const params = e ? e.parameter : {};
    const action = params.action || 'getCards';
    const sheetName = params.sheet || '16. Others & Toxic';

    // 1. Action: Ping ตรวจสอบสถานะการเชื่อมต่อ (เสี้ยววินาที)
    if (action === 'ping') {
      return jsonResponse_({ success: true, message: 'PharmaCU Flashcard API is Live 🚀', timestamp: new Date().toISOString() });
    }

    // 2. Action: ดึงข้อมูลการ์ดทั้งหมดในแผ่นชีตที่ระบุ (เร็วมาก < 1 วินาที)
    if (action === 'getCards') {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      const sheet = ss.getSheetByName(sheetName);
      if (!sheet) return jsonResponse_({ success: false, error: 'Sheet not found: ' + sheetName });

      const lastRow = sheet.getLastRow();
      if (lastRow < 3) return jsonResponse_({ success: true, count: 0, cards: [] });

      // ดึงข้อมูลทั้งตารางในครั้งเดียว (เร็วมาก)
      const values = sheet.getRange(3, 1, lastRow - 2, 8).getValues();

      // ดึง In-Cell Images Map (จาก Cache หรือสแกน XLSX)
      const inCellImages = getCachedInCellImages_();

      const cards = [];
      for (let i = 0; i < values.length; i++) {
        const rowNum = i + 3;
        const row = values[i];

        const itemNo = String(row[0] || '').trim();
        const questionText = String(row[1] || '').trim();
        let qVal = row[2];
        const answerText = String(row[3] || '').trim();
        let aVal = row[4];
        const subtopic = String(row[5] || '').trim();
        const note = String(row[6] || '').trim();
        const track = String(row[7] || 'Clinic').trim();

        if (!itemNo && !questionText) continue;

        // ดึง Image URL สำหรับคำถาม (Column C)
        let qUrl = resolveImageUrl_(qVal, sheetName, rowNum, 2, inCellImages);

        // ดึง Image URL สำหรับเฉลย (Column E)
        let aUrl = resolveImageUrl_(aVal, sheetName, rowNum, 4, inCellImages);

        cards.push({
          id: sheetName + '::' + rowNum,
          itemNo: itemNo || String(cards.length + 1),
          group: sheetName,
          subTopic: subtopic || sheetName,
          track: track,
          question: questionText,
          questionImage: qUrl,
          answer: answerText,
          answerImage: aUrl,
          note: note
        });
      }

      return jsonResponse_({ success: true, sheet: sheetName, count: cards.length, cards: cards });
    }

    // 3. Action: บังคับ Refresh รูปภาพในเซลล์ใหม่ทั้งหมด
    if (action === 'refreshImages') {
      CacheService.getScriptCache().remove('in_cell_images_map');
      const freshImages = getCachedInCellImages_();
      return jsonResponse_({ success: true, message: 'In-cell images refreshed', count: Object.keys(freshImages).length, images: freshImages });
    }

    return jsonResponse_({ success: true, message: 'PharmaCU Flashcard API is Live 🚀', timestamp: new Date().toISOString() });
  } catch (err) {
    return jsonResponse_({ success: false, error: err.toString() });
  }
}

/**
 * ดึง Image URL อย่างฉลาด (รองรับทั้ง Object CellImage, URL ตรง, และ In-Cell Image Map)
 */
function resolveImageUrl_(val, sheetName, rowNum, colIdx, inCellImages) {
  if (!val) return inCellImages[sheetName + '_r' + rowNum + '_c' + colIdx] || '';
  
  // 1. ถ้าเป็น CellImage Object ใน Google Apps Script
  if (typeof val === 'object') {
    try {
      if (val.getContentUrl) {
        const directUrl = val.getContentUrl();
        if (directUrl) return directUrl;
      }
      if (val.getUrl) {
        const u = val.getUrl();
        if (u) return u;
      }
    } catch(e) {}
    return inCellImages[sheetName + '_r' + rowNum + '_c' + colIdx] || '';
  }

  const sVal = String(val).trim();
  if (sVal === 'CellImage') {
    return inCellImages[sheetName + '_r' + rowNum + '_c' + colIdx] || '';
  }

  // 2. ถ้าเป็น URL หรือ Path ปกติ
  if (sVal.indexOf('http') === 0 || sVal.indexOf('images/') === 0 || sVal.indexOf('drive.google') !== -1) {
    return sVal;
  }

  return inCellImages[sheetName + '_r' + rowNum + '_c' + colIdx] || '';
}

/**
 * ดึง In-Cell Images Map พร้อมแคชใน CacheService (อายุ 6 ชั่วโมง)
 */
function getCachedInCellImages_() {
  const cache = CacheService.getScriptCache();
  const cachedJson = cache.get('in_cell_images_map');
  if (cachedJson) {
    try { return JSON.parse(cachedJson); } catch(e) {}
  }

  const freshMap = extractInCellImagesFromXlsx_();
  try {
    cache.put('in_cell_images_map', JSON.stringify(freshMap), 21600); // 6 hours
  } catch(e) {
    // ถ้าขนาดข้อมูลใหญ่เกินแคช ให้ข้าม
  }
  return freshMap;
}

/**
 * สกัดภาพที่แทรกในเซลล์ทั้งหมดผ่าน XLSX Stream
 */
function extractInCellImagesFromXlsx_() {
  const imagesMap = {};
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const url = 'https://docs.google.com/spreadsheets/d/' + ss.getId() + '/export?format=xlsx';
    const res = UrlFetchApp.fetch(url, {
      headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
      muteHttpExceptions: true
    });
    if (res.getResponseCode() !== 200) return imagesMap;

    const zipBlobs = Utilities.unzip(res.getBlob().setContentType('application/zip'));
    const zipMap = {};
    for (let i = 0; i < zipBlobs.length; i++) zipMap[zipBlobs[i].getName()] = zipBlobs[i];

    const sheetFilesMap = {};
    if (zipMap['xl/workbook.xml'] && zipMap['xl/_rels/workbook.xml.rels']) {
      const wbDoc = XmlService.parse(zipMap['xl/workbook.xml'].getDataAsString());
      const wbRelsDoc = XmlService.parse(zipMap['xl/_rels/workbook.xml.rels'].getDataAsString());
      const sheets = wbDoc.getRootElement().getDescendants();
      const rIdToName = {};
      for (let i = 0; i < sheets.length; i++) {
        const el = sheets[i].asElement();
        if (el && el.getName() === 'sheet') {
          rIdToName[el.getAttribute('id', el.getNamespace('r')).getValue()] = el.getAttribute('name').getValue();
        }
      }
      const rels = wbRelsDoc.getRootElement().getDescendants();
      for (let i = 0; i < rels.length; i++) {
        const el = rels[i].asElement();
        if (el && el.getName() === 'Relationship') {
          const rId = el.getAttribute('Id').getValue();
          if (rIdToName[rId]) sheetFilesMap[el.getAttribute('Target').getValue()] = rIdToName[rId];
        }
      }
    }

    const drawingToSheet = {};
    for (const path in zipMap) {
      if (path.indexOf('xl/worksheets/_rels/') === 0 && path.indexOf('.rels') !== -1) {
        const sheetXmlPath = 'worksheets/' + path.replace('xl/worksheets/_rels/', '').replace('.rels', '');
        const sheetName = sheetFilesMap[sheetXmlPath];
        if (!sheetName) continue;
        const relsDoc = XmlService.parse(zipMap[path].getDataAsString());
        const rels = relsDoc.getRootElement().getDescendants();
        for (let i = 0; i < rels.length; i++) {
          const el = rels[i].asElement();
          if (el && el.getName() === 'Relationship') {
            const target = el.getAttribute('Target').getValue();
            if (target.indexOf('drawing') !== -1) drawingToSheet[target.split('/').pop()] = sheetName;
          }
        }
      }
    }

    for (const dName in drawingToSheet) {
      const sheetName = drawingToSheet[dName];
      const dPath = 'xl/drawings/' + dName;
      const dRelsPath = 'xl/drawings/_rels/' + dName + '.rels';
      if (!zipMap[dPath] || !zipMap[dRelsPath]) continue;

      const dRelsDoc = XmlService.parse(zipMap[dRelsPath].getDataAsString());
      const dRels = dRelsDoc.getRootElement().getDescendants();
      const mediaMap = {};
      for (let i = 0; i < dRels.length; i++) {
        const el = dRels[i].asElement();
        if (el && el.getName() === 'Relationship') {
          mediaMap[el.getAttribute('Id').getValue()] = 'xl/' + el.getAttribute('Target').getValue().replace('../', '');
        }
      }

      const dDoc = XmlService.parse(zipMap[dPath].getDataAsString());
      const anchors = dDoc.getRootElement().getChildren();
      for (let i = 0; i < anchors.length; i++) {
        let col = null, row = null, embedId = null;
        const descendants = anchors[i].getDescendants();
        for (let j = 0; j < descendants.length; j++) {
          const el = descendants[j].asElement();
          if (!el) continue;
          if (el.getName() === 'col' && col === null) col = parseInt(el.getText(), 10);
          else if (el.getName() === 'row' && row === null) row = parseInt(el.getText(), 10) + 1;
          else if (el.getName() === 'blip') {
            const attr = el.getAttribute('embed', el.getNamespace('r'));
            if (attr) embedId = attr.getValue();
          }
        }
        if (col !== null && row !== null && embedId && mediaMap[embedId]) {
          const blob = zipMap[mediaMap[embedId]];
          if (blob) {
            imagesMap[sheetName + '_r' + row + '_c' + col] = 'data:' + (blob.getContentType() || 'image/png') + ';base64,' + Utilities.base64Encode(blob.getBytes());
          }
        }
      }
    }
  } catch (err) {
    Logger.log('In-cell error: ' + err);
  }
  return imagesMap;
}

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
