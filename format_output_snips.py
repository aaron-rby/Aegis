from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
from pathlib import Path
P=Path(__file__).parent
src=Path(r'C:\Users\aaron\AppData\Local\Packages\sandbox.{5c9cc39c-2db3-459d-a22b-0b93852ab8b6}\AC\Temp\browser-use\exports\25BCE2640 ESA LAB8 ASSESSMENTv2.docx-15e5c59b-4aee-4915-aa71-c998365048b8.docx')
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';ns={'w':W[1:-1],'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
def prop(p,name,attrs):
    x=p.find('w:'+name,ns)
    if x is None:x=E.SubElement(p,W+name)
    for k,v in attrs.items():x.set(W+k,str(v))
    return x
with ZipFile(src) as z:
    root=E.fromstring(z.read('word/document.xml'));body=root.find('w:body',ns)
    text_before=''.join(root.xpath('//w:t/text()',namespaces=ns));pictures_before=len(root.findall('.//w:drawing',ns))
    count=0
    for heading in list(body):
        if heading.tag!=W+'p' or ''.join(heading.xpath('.//w:t/text()',namespaces=ns)).strip().lower().rstrip(':')!='output snips':continue
        table=heading.getnext()
        if table is None or table.tag!=W+'tbl':continue
        pp=prop(heading,'pPr',{});prop(pp,'pageBreakBefore',{'val':1});prop(pp,'keepNext',{'val':1});prop(pp,'spacing',{'after':160})
        rows=table.findall('w:tr',ns);new=[]
        for col in range(2):
            for row in rows:
                cells=row.findall('w:tc',ns)
                if col>=len(cells):continue
                for p in cells[col].findall('w:p',ns):
                    if not p.findall('.//w:drawing',ns) and not ''.join(p.xpath('.//w:t/text()',namespaces=ns)).strip():continue
                    p=deepcopy(p);pp=prop(p,'pPr',{});prop(pp,'jc',{'val':'center'});prop(pp,'ind',{'left':0,'right':0,'firstLine':0});prop(pp,'spacing',{'before':0,'after':100,'line':240,'lineRule':'auto'});prop(pp,'keepNext',{'val':1});prop(pp,'keepLines',{'val':1})
                    for drawing in p.findall('.//w:drawing',ns):
                        extent=drawing.find('.//wp:extent',ns)
                        if extent is not None:
                            cx=int(extent.get('cx'));cy=int(extent.get('cy'));scale=min(1,210*12700/cy,420*12700/cx)
                            extent.set('cx',str(round(cx*scale)));extent.set('cy',str(round(cy*scale)))
                            for size in drawing.findall('.//a:xfrm/a:ext',ns):size.set('cx',str(round(cx*scale)));size.set('cy',str(round(cy*scale)))
                    new.append(p)
        if new:prop(prop(new[-1],'pPr',{}),'keepNext',{'val':0})
        following=table.getnext()
        if following is not None and following.tag==W+'p' and ''.join(following.xpath('.//w:t/text()',namespaces=ns)).strip()=='Result':prop(prop(following,'pPr',{}),'pageBreakBefore',{'val':1})
        index=body.index(table);body.remove(table)
        for p in new:body.insert(index,p);index+=1
        count+=1
    # Captions move with their corresponding pictures; compare text as a multiset.
    import collections
    assert collections.Counter(root.xpath('//w:t/text()',namespaces=ns))==collections.Counter(E.fromstring(z.read('word/document.xml')).xpath('//w:t/text()',namespaces=ns))
    assert pictures_before==len(root.findall('.//w:drawing',ns))
    out=P/'assessment-output-snips.docx'
    with ZipFile(out,'w',ZIP_DEFLATED) as dest:
        for item in z.infolist():dest.writestr(item,E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
print('Output sections arranged:',count,'Images retained:',pictures_before)
print(out)
