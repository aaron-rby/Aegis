from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
from pathlib import Path
P=Path(__file__).parent
src=Path(r'C:\Users\aaron\AppData\Local\Packages\sandbox.{5c9cc39c-2db3-459d-a22b-0b93852ab8b6}\AC\Temp\browser-use\exports\25BCE2640 ESA LAB8 ASSESSMENTv2.docx-3e8ca601-5644-44bf-8bf9-a387368d33d3.docx')
ref=Path(r'C:\Users\aaron\Downloads\ESA_lab_assessment_8_docs.docx')
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';ns={'w':W[1:-1]}
def el(p,name,attrs):
    x=p.find('w:'+name,ns)
    if x is None:x=E.SubElement(p,W+name)
    for k,v in attrs.items():x.set(W+k,str(v))
    return x
with ZipFile(src) as z,ZipFile(ref) as rz:
    parts={x.filename:z.read(x.filename) for x in z.infolist()}
    root=E.fromstring(parts['word/document.xml']);original=''.join(root.xpath('//w:t/text()',namespaces=ns))
    body=root.find('w:body',ns);count=0
    labels={'Aim of the Experiment','Tools Required','Brief Theory','Circuit Diagram','Circuit Connections','Algorithm','Flowchart','Flow Chart','Program','Code','Arduino Code','Procedure','Output','Result','Results','Inference','Hardware Connections','Source Code','Observations'}
    changed=[]
    for p in body.findall('w:p',ns):
        text=''.join(p.xpath('.//w:t/text()',namespaces=ns)).strip()
        pp=el(p,'pPr',{});style=pp.find('w:pStyle',ns);sid=style.get(W+'val','') if style is not None else ''
        ishead=('heading' in sid.lower() or text.rstrip(':') in labels or text.lower() in {'arduino code with comments','output snips','procedure to perform the aim','contents'} or (text.startswith('Program ') and len(text)<25))
        if ishead and text:
            major=text.startswith('Program ') or text=='ESA Lab Assessment report'
            spacing=el(pp,'spacing',{'after':160 if major else 120})
            el(pp,'keepNext',{'val':1});el(pp,'keepLines',{'val':1})
            changed.append(text)
    source=E.fromstring(rz.read('word/document.xml'));source_table=source.find('w:body',ns).findall('w:tbl',ns)[-1]
    table=body.findall('w:tbl',ns)[-1]
    for old,new in zip(table.findall('w:tr',ns)[-2:],source_table.findall('w:tr',ns)[-2:]):
        row=deepcopy(new)
        for p in row.findall('.//w:p',ns):
            pp=el(p,'pPr',{});el(pp,'pStyle',{'val':'Normal'})
            for r in p.findall('w:r',ns):
                rp=el(r,'rPr',{});el(rp,'rFonts',{'ascii':'Arial','hAnsi':'Arial','eastAsia':'Arial','cs':'Arial'});el(rp,'sz',{'val':22});el(rp,'szCs',{'val':22})
        for b in row.xpath('.//w:bookmarkStart|.//w:bookmarkEnd',namespaces=ns):b.getparent().remove(b)
        table.replace(old,row)
    assert original==''.join(root.xpath('//w:t/text()',namespaces=ns))
    parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
    headerparts=[]
    for name,data in list(parts.items()):
        if name.startswith(('word/header','word/footer')) and name.endswith('.xml'):
            x=E.fromstring(data)
            for rp in x.findall('.//w:rPr',ns):
                f=el(rp,'rFonts',{'ascii':'Calibri','hAnsi':'Calibri','eastAsia':'Calibri','cs':'Calibri'})
                for a in list(f.attrib):
                    if 'Theme' in a:f.attrib.pop(a)
            for r in x.findall('.//w:r',ns):
                rp=el(r,'rPr',{});el(rp,'rFonts',{'ascii':'Calibri','hAnsi':'Calibri','eastAsia':'Calibri','cs':'Calibri'})
            parts[name]=E.tostring(x,xml_declaration=True,encoding='UTF-8',standalone=True);headerparts.append(name)
    out=P/'assessment-polished.docx'
    with ZipFile(out,'w',ZIP_DEFLATED) as dest:
        for name,data in parts.items():dest.writestr(name,data)
print('Heading spacing:',changed)
print('Calibri:',headerparts)
print('Signature rows copied directly from reference; text preserved')
print(out)
