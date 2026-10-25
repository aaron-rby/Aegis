from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
from pathlib import Path
P=Path(__file__).parent;src=Path(r'C:\Users\aaron\AppData\Local\Packages\sandbox.{5c9cc39c-2db3-459d-a22b-0b93852ab8b6}\AC\Temp\browser-use\exports\25BCE2640 ESA LAB8 ASSESSMENTv2.docx-f20b5004-336d-4381-be60-fe584a6d80bc.docx')
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';n={'w':W[1:-1]}
def prop(p,k,a):
    x=p.find('w:'+k,n)
    if x is None:x=E.SubElement(p,W+k)
    for key,val in a.items():x.set(W+key,str(val))
    return x
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=n)).strip()
def replace_text(p,s):
    for c in list(p):
        if c.tag!=W+'pPr':p.remove(c)
    r=E.SubElement(p,W+'r');rp=E.SubElement(r,W+'rPr');prop(rp,'rFonts',{'ascii':'Times New Roman','hAnsi':'Times New Roman'});prop(rp,'sz',{'val':24});E.SubElement(r,W+'t').text=s
with ZipFile(src) as z:
    parts={i.filename:z.read(i.filename) for i in z.infolist()};root=E.fromstring(parts['word/document.xml']);body=root.find('w:body',n)
    num=E.fromstring(parts['word/numbering.xml']);aid=max([int(x.get(W+'abstractNumId')) for x in num.findall('w:abstractNum',n)]+[-1])+1;nid=max([int(x.get(W+'numId')) for x in num.findall('w:num',n)]+[0])+1
    an=E.SubElement(num,W+'abstractNum',{W+'abstractNumId':str(aid)});lvl=E.SubElement(an,W+'lvl',{W+'ilvl':'0'});prop(lvl,'start',{'val':1});prop(lvl,'numFmt',{'val':'bullet'});prop(lvl,'lvlText',{'val':'•'});prop(lvl,'lvlJc',{'val':'left'});prop(prop(lvl,'pPr',{}),'ind',{'left':360,'hanging':180});nu=E.SubElement(num,W+'num',{W+'numId':str(nid)});prop(nu,'abstractNumId',{'val':aid})
    added=0;tools=0
    for p in list(body):
        if p.tag!=W+'p':continue
        s=text(p)
        if s=='Tools Required':
            old=p.getnext();content=text(old).rstrip('.');items=content.split(', ')
            tail=items.pop();items.extend(tail.rsplit(' and ',1))
            idx=body.index(old);body.remove(old)
            for item in items:
                q=deepcopy(old);replace_text(q,item[0].upper()+item[1:]);pp=prop(q,'pPr',{});np=prop(pp,'numPr',{});prop(np,'ilvl',{'val':0});prop(np,'numId',{'val':nid});prop(pp,'spacing',{'before':0,'after':40,'line':240,'lineRule':'auto'});prop(pp,'keepNext',{'val':0});body.insert(idx,q);idx+=1;tools+=1
        if s in ['Procedure','Procedure to Perform the Aim']:
            h=deepcopy(p);replace_text(h,'Manual calculation:');hr=h.find('w:r/w:rPr',n);prop(hr,'b',{'val':1});pp=prop(h,'pPr',{});prop(pp,'spacing',{'before':120,'after':120});prop(pp,'keepNext',{'val':1});prop(pp,'pageBreakBefore',{'val':0})
            none=deepcopy(h);replace_text(none,'None');np=prop(none,'pPr',{});style=np.find('w:pStyle',n)
            if style is not None:np.remove(style)
            prop(np,'spacing',{'before':0,'after':120});prop(np,'keepNext',{'val':1})
            idx=body.index(p);body.insert(idx,h);body.insert(idx+1,none);added+=1
    parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True);parts['word/numbering.xml']=E.tostring(num,xml_declaration=True,encoding='UTF-8',standalone=True)
    out=P/'assessment-calculations-tools.docx'
    with ZipFile(out,'w',ZIP_DEFLATED) as dest:
        for k,v in parts.items():dest.writestr(k,v)
print('Manual calculation sections:',added,'Tool bullets:',tools)
