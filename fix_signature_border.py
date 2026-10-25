from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from pathlib import Path
P=Path(__file__).parent
src=Path(r'C:\Users\aaron\AppData\Local\Packages\sandbox.{5c9cc39c-2db3-459d-a22b-0b93852ab8b6}\AC\Temp\browser-use\exports\25BCE2640 ESA LAB8 ASSESSMENTv2.docx-6cc187ef-b29a-451e-b11c-a0a0d404a793.docx')
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';n={'w':W[1:-1]}
def prop(p,name,attrs):
    x=p.find('w:'+name,n)
    if x is None:x=E.SubElement(p,W+name)
    for k,v in attrs.items():x.set(W+k,str(v))
    return x
with ZipFile(src) as z:
    r=E.fromstring(z.read('word/document.xml'));before=r.xpath('//w:t/text()',namespaces=n)
    tables=[t for t in r.findall('w:body/w:tbl',n) if 'Signature of TRA' in ''.join(t.xpath('.//w:t/text()',namespaces=n)) and len(t.findall('w:tr',n))==1]
    assert len(tables)==1
    t=tables[0];tp=prop(t,'tblPr',{});prop(tp,'tblW',{'w':3024,'type':'dxa'});prop(tp,'tblInd',{'w':0,'type':'dxa'});prop(tp,'jc',{'val':'left'})
    borders=prop(tp,'tblBorders',{})
    for side in ['top','bottom','left','right']:prop(borders,side,{'val':'single','sz':8,'color':'000000','space':0})
    grid=t.find('w:tblGrid',n)
    for col in grid:col.set(W+'w','3024')
    row=t.find('w:tr',n);prop(prop(row,'trPr',{}),'trHeight',{'val':948,'hRule':'atLeast'})
    for cell in row.findall('w:tc',n):
        cp=prop(cell,'tcPr',{});prop(cp,'tcW',{'w':3024,'type':'dxa'});prop(cp,'vAlign',{'val':'bottom'})
        cb=prop(cp,'tcBorders',{})
        for side in ['top','bottom','left','right']:prop(cb,side,{'val':'single','sz':8,'color':'000000','space':0})
        mar=prop(cp,'tcMar',{})
        for side in ['left','right','top','bottom']:prop(mar,side,{'w':100,'type':'dxa'})
        for p in cell.findall('w:p',n):
            pp=prop(p,'pPr',{});prop(pp,'jc',{'val':'center'});prop(pp,'spacing',{'before':0,'after':0})
    assert before==r.xpath('//w:t/text()',namespaces=n)
    out=P/'assessment-signature-box-fixed.docx'
    with ZipFile(out,'w',ZIP_DEFLATED) as dest:
        for item in z.infolist():dest.writestr(item,E.tostring(r,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
print('Signature box: 151.2 x 47.4 pt minimum; explicit black 1 pt borders; text unchanged')
