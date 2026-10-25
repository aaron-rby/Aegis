from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
from pathlib import Path
import hashlib
P=Path(__file__).parent; source=Path(r'C:\Users\aaron\Downloads\ESA_lab_assessment_8_docs.docx')
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'; R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
n={'w':W[1:-1]}
with ZipFile(source) as s,ZipFile(P/'assessment-formatted.docx') as d:
    st=E.fromstring(s.read('word/document.xml'));dt=E.fromstring(d.read('word/document.xml'))
    sb=st.find('w:body',n);db=dt.find('w:body',n)
    original_text=''.join(dt.xpath('//w:t/text()',namespaces=n))
    old=db.findall('w:tbl',n)[-1];new=deepcopy(sb.findall('w:tbl',n)[-1]);heading=deepcopy(sb.findall('w:tbl',n)[-1].getprevious())
    for sr,dr in zip(new.findall('w:tr',n),old.findall('w:tr',n)):
        for sc,dc in zip(sr.findall('w:tc',n),dr.findall('w:tc',n)):
            text=''.join(dc.xpath('.//w:t/text()',namespaces=n))
            if ''.join(sc.xpath('.//w:t/text()',namespaces=n))==text:continue
            ts=sc.findall('.//w:t',n)
            if ts:
                ts[0].text=text;ts[0].set('{http://www.w3.org/XML/1998/namespace}space','preserve')
                for t in ts[1:]:t.text=''
    styles=E.fromstring(d.read('word/styles.xml'));ss=E.fromstring(s.read('word/styles.xml'))
    sm={x.get(W+'styleId'):x for x in ss.findall('w:style',n)};copied=set()
    def style(k):
        if k in copied or k not in sm:return
        copied.add(k);x=deepcopy(sm[k]);x.set(W+'styleId','RefLast'+k);x.attrib.pop(W+'default',None)
        for tag in ['basedOn','next','link']:
            el=x.find('w:'+tag,n)
            if el is not None:
                v=el.get(W+'val');style(v);el.set(W+'val','RefLast'+v)
        styles.append(x)
    for block in [heading,new]:
        for el in block.xpath('.//w:pStyle|.//w:rStyle|.//w:tblStyle',namespaces=n):
            k=el.get(W+'val');style(k);el.set(W+'val','RefLast'+k)
        for p in block.findall('.//w:p',n)+([block] if block.tag==W+'p' else []):
            pp=p.find('w:pPr',n)
            if pp is None:pp=E.Element(W+'pPr');p.insert(0,pp)
            if pp.find('w:pStyle',n) is None:
                style('Normal');el=E.Element(W+'pStyle');el.set(W+'val','RefLastNormal');pp.insert(0,el)
        for run in block.findall('.//w:r',n):
            rp=run.find('w:rPr',n)
            if rp is None:rp=E.Element(W+'rPr');run.insert(0,rp)
            for default in ss.find('w:docDefaults/w:rPrDefault/w:rPr',n):
                if block is heading and default.tag in [W+'sz',W+'szCs']:continue
                if rp.find(default.tag) is None:rp.append(deepcopy(default))
        for el in block.xpath('.//w:bookmarkStart|.//w:bookmarkEnd|.//w:lastRenderedPageBreak',namespaces=n):el.getparent().remove(el)
        # Keep visible text and run formatting without importing reference hyperlinks.
        for link in block.findall('.//w:hyperlink',n):
            parent=link.getparent();i=parent.index(link)
            for child in list(link):parent.insert(i,deepcopy(child));i+=1
            parent.remove(link)
    db.replace(old.getprevious(),heading);db.replace(old,new)
    out=P/'assessment-reference-format.docx'
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        for item in d.infolist():
            data=E.tostring(dt,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else E.tostring(styles,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/styles.xml' else d.read(item.filename)
            z.writestr(item,data)
    assert ''.join(dt.xpath('//w:t/text()',namespaces=n))==original_text
(P/'artifact.md').write_text('Reference: '+str(source)+'\nSHA256: '+hashlib.sha256(source.read_bytes()).hexdigest()+'\nScope: copy final heading and 19-row table verbatim, including grid, merges, borders, cell margins, row sizes, alignment and source typography. Preserve destination cell text and all other document parts. Import source styles under RefLast prefix. Source default table typography Arial 11pt; heading Times New Roman with source Heading1. Browser render used because bundled LibreOffice is unavailable.\n')
print(out)
