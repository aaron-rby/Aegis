from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
from pathlib import Path
src=Path(r'C:\Users\aaron\AppData\Local\Packages\sandbox.{5c9cc39c-2db3-459d-a22b-0b93852ab8b6}\AC\Temp\browser-use\exports\25BCE2640 ESA LAB8 ASSESSMENTv2.docx-045ef378-da5b-4415-88b1-044d95d65b9f.docx')
out=Path(__file__).parent/'assessment-no-bookmarks.docx'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
count=0
with ZipFile(src) as z,ZipFile(out,'w',ZIP_DEFLATED) as dest:
    for item in z.infolist():
        data=z.read(item.filename)
        if item.filename.startswith('word/') and item.filename.endswith('.xml'):
            root=E.fromstring(data)
            bookmarks=root.xpath('//w:bookmarkStart|//w:bookmarkEnd',namespaces=ns)
            if bookmarks:
                before=root.xpath('//w:t/text()',namespaces=ns)
                count+=len(root.xpath('//w:bookmarkStart',namespaces=ns))
                for el in bookmarks:el.getparent().remove(el)
                assert before==root.xpath('//w:t/text()',namespaces=ns)
                data=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
        dest.writestr(item,data)
print('Bookmarks removed:',count)
print(out)
