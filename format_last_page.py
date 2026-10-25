from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
from pathlib import Path
root=Path(__file__).parent
src=root/'assessment-original.docx'; out=root/'assessment-formatted.docx'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W='{'+ns['w']+'}'
def setel(parent,name,attrs):
    el=parent.find('w:'+name,ns)
    if el is None: el=E.SubElement(parent,W+name)
    for k,v in attrs.items(): el.set(W+k,str(v))
    return el
with ZipFile(src) as z:
    tree=E.fromstring(z.read('word/document.xml'))
    body=tree.find('w:body',ns); table=body.findall('w:tbl',ns)[-1]
    heading=table.getprevious()
    while heading is not None and heading.tag!=W+'p': heading=heading.getprevious()
    pp=setel(heading,'pPr',{})
    setel(pp,'jc',{'val':'center'});setel(pp,'ind',{'left':0,'right':0,'firstLine':0})
    setel(pp,'spacing',{'before':0,'after':120,'line':240,'lineRule':'auto'})
    setel(pp,'keepNext',{'val':1});setel(pp,'pageBreakBefore',{'val':1})
    for r in heading.findall('.//w:r',ns):
        rp=setel(r,'rPr',{});setel(rp,'sz',{'val':32});setel(rp,'szCs',{'val':32});setel(rp,'b',{'val':0})
    widths=[800,4100,2600,1500]
    grid=table.find('w:tblGrid',ns)
    for el,width in zip(grid,widths): el.set(W+'w',str(width))
    tp=setel(table,'tblPr',{});setel(tp,'tblW',{'w':9000,'type':'dxa'});setel(tp,'tblInd',{'w':0,'type':'dxa'})
    setel(tp,'jc',{'val':'center'});setel(tp,'tblLayout',{'type':'fixed'})
    for i,row in enumerate(table.findall('w:tr',ns)):
        trp=setel(row,'trPr',{});setel(trp,'trHeight',{'val':340 if i<7 else 460,'hRule':'atLeast'})
        setel(trp,'cantSplit',{})
        col=0
        for cell in row.findall('w:tc',ns):
            cp=setel(cell,'tcPr',{});span=cp.find('w:gridSpan',ns);n=int(span.get(W+'val')) if span is not None else 1
            setel(cp,'tcW',{'w':sum(widths[col:col+n]),'type':'dxa'});col+=n
            setel(cp,'vAlign',{'val':'center'})
            margins=setel(cp,'tcMar',{})
            for side,v in [('top',50),('bottom',50),('left',80),('right',80)]:setel(margins,side,{'w':v,'type':'dxa'})
            for p in cell.findall('.//w:p',ns):
                pp=setel(p,'pPr',{});setel(pp,'spacing',{'before':0,'after':0,'line':240,'lineRule':'auto'})
                setel(pp,'keepNext',{'val':0});setel(pp,'keepLines',{'val':1})
                for r in p.findall('w:r',ns):
                    rp=setel(r,'rPr',{});setel(rp,'sz',{'val':20});setel(rp,'szCs',{'val':20})
                    setel(rp,'rFonts',{'ascii':'Times New Roman','hAnsi':'Times New Roman'})
    with ZipFile(out,'w',ZIP_DEFLATED) as oz:
        for item in z.infolist():oz.writestr(item,E.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True) if item.filename=='word/document.xml' else z.read(item.filename))
print(out)
