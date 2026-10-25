from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from pathlib import Path
P=Path(__file__).parent;n={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
src=P/'assessment-output-snips.docx';out=P/'assessment-output-final.docx'
with ZipFile(src) as z:
    r=E.fromstring(z.read('word/document.xml'));t=r.findall('w:body/w:tbl',n)[1]
    nums=['3, 7, 12, 17']*4+['3, 7, 12, 17','3, 8, 13, 18','None','4, 9, 14, 18','5, 10, 15, 20','6, 11, 16, 21','6, 11, 16, 21']
    for row,num in zip(t.findall('w:tr',n)[1:],nums):
        cell=row.findall('w:tc',n)[1];texts=cell.findall('.//w:t',n)
        texts[0].text=num
        for x in texts[1:]:x.text=''
    with ZipFile(out,'w',ZIP_DEFLATED) as d:
        for item in z.infolist():d.writestr(item,E.tostring(r,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
print(out)
