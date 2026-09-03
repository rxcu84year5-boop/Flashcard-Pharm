/**
 * =========================================================================
 * 🧬 PharmaCU Flashcard Private — Live Web App API Engine (Code.gs)
 * =========================================================================
 * ติดตั้งใน Google Sheet: Extensions (ส่วนขยาย) > Apps Script
 * Deploy เป็น Web App:
 *   1. คลิก "Deploy" (การทำให้ใช้งานได้) > "New deployment" (การทำให้ใช้งานได้ใหม่)
 *   2. เลือกประเภท "Web app" (เว็บแอป)
 *   3. Execute as: "Me" (ฉัน)
 *   4. Who has access: "Anyone" (ทุกคน)
 *   5. คลิก Deploy แล้วคัดลอก Web App URL มาใส่ใน index.html
 * =========================================================================
 */

function doGet(e) {
  try {
    const params = e ? e.parameter : {};
    const action = params.action || 'getCards';
    const sheetName = params.sheet || '16. Others & Toxic';

    // 1. Action: ดึงรูปภาพทั้งหมดในเซลล์ของทุกแผ่นชีต (Base64 Data URIs)
    if (action === 'getImages') {
      const imagesMap = extractInCellImages_();
      return jsonResponse_({ success: true, count: Object.keys(imagesMap).length, images: imagesMap });
    }

    // 2. Action: ดึงข้อมูลการ์ดทั้งหมดในแผ่นชีตที่ระบุ พร้อมรูปภาพสดๆ ในเซลล์
    if (action === 'getCards') {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      const sheet = ss.getSheetByName(sheetName);
      if (!sheet) {
        return jsonResponse_({ success: false, error: 'Sheet not found: ' + sheetName });
      }

      // ดึงรูปภาพในเซลล์สดๆ
      const inCellImages = extractInCellImages_();

      const lastRow = sheet.getLastRow();
      if (lastRow < 3) {
        return jsonResponse_({ success: true, count: 0, cards: [] });
      }

      const range = sheet.getRange(3, 1, lastRow - 2, 8);
      const values = range.getValues();
      const richTextValues = range.getRichTextValues();

      const cards = [];
      for (let i = 0; i < values.length; i++) {
        const rowNum = i + 3; // แถวจริงในชีต
        const row = values[i];
        const rtRow = richTextValues[i];

        const itemNo = String(row[0] || '').trim();
        const questionText = String(row[1] || '').trim();
        let qUrl = String(row[2] || '').trim();
        const answerText = String(row[3] || '').trim();
        let aUrl = String(row[4] || '').trim();
        const subtopic = String(row[5] || '').trim();
        const note = String(row[6] || '').trim();
        const track = String(row[7] || 'Clinic').trim();

        if (!itemNo && !questionText) continue;

        // ตรวจสอบรูปภาพในเซลล์ Column C (Col 3 ใน 1-based, index 2)
        const cellCKey = sheetName + '_r' + rowNum + '_c2';
        if (!qUrl && inCellImages[cellCKey]) {
          qUrl = inCellImages[cellCKey];
        }

        // ตรวจสอบรูปภาพในเซลล์ Column E (Col 5 ใน 1-based, index 4)
        const cellEKey = sheetName + '_r' + rowNum + '_c4';
        if (!aUrl && inCellImages[cellEKey]) {
          aUrl = inCellImages[cellEKey];
        }

        // แปลง RichText เป็น HTML สำหรับสีและรูปแบบ
        const qHtml = formatRichText_(rtRow[1], questionText);
        const aHtml = formatRichText_(rtRow[3], answerText);

        cards.push({
          id: sheetName + '::' + rowNum,
          itemNo: itemNo || String(cards.length + 1),
          group: sheetName,
          subTopic: subtopic || sheetName,
          track: track,
          question: qHtml,
          questionImage: qUrl,
          answer: aHtml,
          answerImage: aUrl,
          note: note
        });
      }

      return jsonResponse_({
        success: true,
        sheet: sheetName,
        count: cards.length,
        cards: cards
      });
    }

    // 3. Action: Ping ตรวจสอบการเชื่อมต่อ
    return jsonResponse_({ success: true, message: 'PharmaCU Flashcard API is Live 🚀', timestamp: new Date().toISOString() });

  } catch (err) {
    return jsonResponse_({ success: false, error: err.toString() });
  }
}

/**
 * ดึงภาพที่แทรกในเซลล์ (In-Cell Images / Pasted Blobs) โดยการ Parse XLSX ในหน่วยความจำ
 * ส่งคืนเป็น JSON Map: { "SheetName_r127_c2": "data:image/png;base64,..." }
 */
function extractInCellImages_() {
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
    for (let i = 0; i < zipBlobs.length; i++) {
      zipMap[zipBlobs[i].getName()] = zipBlobs[i];
    }

    // 1. Map sheet XML to Sheet Name
    const sheetFilesMap = {};
    if (zipMap['xl/workbook.xml'] && zipMap['xl/_rels/workbook.xml.rels']) {
      const wbDoc = XmlService.parse(zipMap['xl/workbook.xml'].getDataAsString());
      const wbRelsDoc = XmlService.parse(zipMap['xl/_rels/workbook.xml.rels'].getDataAsString());

      const sheets = wbDoc.getRootElement().getDescendants();
      const rIdToName = {};
      for (let i = 0; i < sheets.length; i++) {
        const el = sheets[i].asElement();
        if (el && el.getName() === 'sheet') {
          const sName = el.getAttribute('name').getValue();
          const rId = el.getAttribute('id', el.getNamespace('r')).getValue();
          rIdToName[rId] = sName;
        }
      }

      const rels = wbRelsDoc.getRootElement().getDescendants();
      for (let i = 0; i < rels.length; i++) {
        const el = rels[i].asElement();
        if (el && el.getName() === 'Relationship') {
          const rId = el.getAttribute('Id').getValue();
          const target = el.getAttribute('Target').getValue();
          if (rIdToName[rId]) {
            sheetFilesMap[target] = rIdToName[rId];
          }
        }
      }
    }

    // 2. Map Sheet to Drawing XML
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
            if (target.indexOf('drawing') !== -1) {
              const dName = target.split('/').pop();
              drawingToSheet[dName] = sheetName;
            }
          }
        }
      }
    }

    // 3. Parse Drawings and Extract Coordinates
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
          const rId = el.getAttribute('Id').getValue();
          const target = el.getAttribute('Target').getValue();
          mediaMap[rId] = 'xl/' + target.replace('../', '');
        }
      }

      const dDoc = XmlService.parse(zipMap[dPath].getDataAsString());
      const anchors = dDoc.getRootElement().getChildren();

      for (let i = 0; i < anchors.length; i++) {
        const anchor = anchors[i];
        let col = null;
        let row = null;
        let embedId = null;

        const descendants = anchor.getDescendants();
        for (let j = 0; j < descendants.length; j++) {
          const el = descendants[j].asElement();
          if (!el) continue;
          if (el.getName() === 'col' && col === null) {
            col = parseInt(el.getText(), 10);
          } else if (el.getName() === 'row' && row === null) {
            row = parseInt(el.getText(), 10) + 1; // 1-based row index
          } else if (el.getName() === 'blip') {
            const embedAttr = el.getAttribute('embed', el.getNamespace('r'));
            if (embedAttr) embedId = embedAttr.getValue();
          }
        }

        if (col !== null && row !== null && embedId && mediaMap[embedId]) {
          const mediaFile = mediaMap[embedId];
          if (zipMap[mediaFile]) {
            const blob = zipMap[mediaFile];
            const base64Data = Utilities.base64Encode(blob.getBytes());
            const mimeType = blob.getContentType() || 'image/png';
            const dataUri = 'data:' + mimeType + ';base64,' + base64Data;
            const key = sheetName + '_r' + row + '_c' + col;
            imagesMap[key] = dataUri;
          }
        }
      }
    }
  } catch (err) {
    Logger.log('In-cell extraction error: ' + err);
  }
  return imagesMap;
}

/**
 * แปลง RichTextValue เป็น HTML พร้อมตกแต่งสีและตัวหนา
 */
function formatRichText_(rtVal, fallbackText) {
  if (!rtVal) return (fallbackText || '').replace(/\n/g, '<br>');
  const text = rtVal.getText();
  if (!text) return '';

  const runs = rtVal.getRuns();
  if (!runs || runs.length <= 1) {
    return escapeHtml_(text).replace(/\n/g, '<br>');
  }

  let html = '';
  for (let i = 0; i < runs.length; i++) {
    const run = runs[i];
    let runText = escapeHtml_(run.getText());
    if (!runText) continue;

    const style = run.getTextStyle();
    if (style.isBold()) runText = '<b>' + runText + '</b>';
    if (style.isItalic()) runText = '<i>' + runText + '</i>';
    if (style.isUnderline()) runText = '<u>' + runText + '</u>';

    const color = style.getForegroundColorObject();
    if (color) {
      const hex = color.asRgbColor().asHexString();
      if (hex && hex !== '#000000') {
        runText = '<span style="color:' + hex + '">' + runText + '</span>';
      }
    }
    html += runText;
  }
  return html.replace(/\n/g, '<br>');
}

function escapeHtml_(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
