from zipfile import ZipFile,ZIP_DEFLATED
from pathlib import Path
from lxml import etree as E
P=Path(__file__).parent
src=Path(r'C:\Users\aaron\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions\08E4136ACFA46000013488ADB9F54F087BFB0CF1\transfers\2026-43\ASSESSMENT-8_25BCE2634_v3.docx')
out=P/'ASSESSMENT-8_25BCE2634_edited-LCD.docx'
with ZipFile(src) as z:
 parts={x.filename:z.read(x.filename) for x in z.infolist()}
 rels=E.fromstring(parts['word/_rels/document.xml.rels']);rel=next(x for x in rels if x.get('Id')=='rId14');rel.set('Target','media/ketan-lcd-edited.png')
 parts['word/_rels/document.xml.rels']=E.tostring(rels,xml_declaration=True,encoding='UTF-8',standalone=True)
 parts['word/media/ketan-lcd-edited.png']=(P/'Ketan-LCD-expected-output-edited.png').read_bytes()
 types=E.fromstring(parts['[Content_Types].xml'])
 if not any(x.get('Extension')=='png' for x in types):E.SubElement(types,'{http://schemas.openxmlformats.org/package/2006/content-types}Default',Extension='png',ContentType='image/png')
 parts['[Content_Types].xml']=E.tostring(types,xml_declaration=True,encoding='UTF-8',standalone=True)
 root=E.fromstring(parts['word/document.xml']);ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}
 for dp in list(root.find('w:body',ns))[282].findall('.//wp:docPr',ns):dp.set('descr','Edited illustration of expected output: Ketan Mulani on row 1; 25BCE2634 on row 2.')
 parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
 with ZipFile(out,'w',ZIP_DEFLATED) as dest:
  for k,v in parts.items():dest.writestr(k,v)
print(out)
