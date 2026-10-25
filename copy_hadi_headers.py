from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from pathlib import Path
import posixpath
P=Path(__file__).parent;src=Path(r'C:\Users\aaron\AppData\Local\Packages\sandbox.{5c9cc39c-2db3-459d-a22b-0b93852ab8b6}\AC\Temp\browser-use\exports\25BCE2640 ESA LAB8 ASSESSMENTv2.docx-c85a5752-b488-484b-b733-89c21541b855.docx');ref=Path(r'C:\Users\aaron\Downloads\ESA_lab_assessment_8_docs.docx')
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}';n={'w':W[1:-1]}
def replace(root,old,new):
 for p in root.findall('.//w:p',n):
  nodes=p.findall('.//w:t',n);full=''.join(x.text or '' for x in nodes);start=full.find(old)
  if start<0:continue
  end=start+len(old);offset=0;placed=False
  for x in nodes:
   s=x.text or '';a=offset;b=a+len(s);offset=b
   if b<=start or a>=end:continue
   left=s[:max(0,start-a)];right=s[max(0,end-a):] if end<b else ''
   x.text=left+(new if not placed else '')+right;x.set('{http://www.w3.org/XML/1998/namespace}space','preserve');placed=True
with ZipFile(src) as z,ZipFile(ref) as h:
 parts={x.filename:z.read(x.filename) for x in z.infolist()};doc=E.fromstring(parts['word/document.xml']);hd=E.fromstring(h.read('word/document.xml'))
 rels=E.fromstring(parts['word/_rels/document.xml.rels']);hr=E.fromstring(h.read('word/_rels/document.xml.rels'));targets={x.get('Id'):posixpath.normpath('word/'+x.get('Target')) for x in rels};ht={x.get('Id'):posixpath.normpath('word/'+x.get('Target')) for x in hr}
 hs=hd.findall('.//w:sectPr',n)[-1];sourceparts={E.QName(x).localname+':'+x.get(W+'type'):ht[x.get(R+'id')] for x in hs if E.QName(x).localname in ['headerReference','footerReference']}
 for sec in doc.findall('.//w:sectPr',n):
  for x in sec:
   key=E.QName(x).localname+':'+str(x.get(W+'type'))
   if key not in sourceparts:continue
   part=targets[x.get(R+'id')];root=E.fromstring(h.read(sourceparts[key]))
   for old,new in [('Abdul Hadi','Aaron Robertson'),('25BCE0553','25BCE2640'),('7594975428','9746244366'),('abdul.hadi2025@vitstudent.ac.in','aaron.robertson2025@vitstudent.ac.in'),('Hardware Interfacing of Led, Servo Motor, Ultrasonic Sensor and LCD with Arduino Uno','Interfacing LED, Servo Motor, Ultrasonic Distance Sensor and LCD Hardware with Arduino Uno')]:replace(root,old,new)
   for b in root.xpath('//w:bookmarkStart|//w:bookmarkEnd',namespaces=n):b.getparent().remove(b)
   for r in root.findall('.//w:r',n):
    rp=r.find('w:rPr',n)
    if rp is None:rp=E.Element(W+'rPr');r.insert(0,rp)
    f=rp.find('w:rFonts',n)
    if f is None:f=E.SubElement(rp,W+'rFonts')
    f.attrib.clear()
    for k in ['ascii','hAnsi','eastAsia','cs']:f.set(W+k,'Calibri')
   # Materialise inherited source font size so target defaults cannot change it.
   for rp in root.findall('.//w:rPr',n):
    if rp.find('w:sz',n) is None:E.SubElement(rp,W+'sz',{W+'val':'22'})
   parts[part]=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
   print(key,part,''.join(root.xpath('//w:t/text()',namespaces=n)))
  margins=sec.find('w:pgMar',n);hm=hs.find('w:pgMar',n)
  for k in ['header','footer']:margins.set(W+k,hm.get(W+k))
 parts['word/document.xml']=E.tostring(doc,xml_declaration=True,encoding='UTF-8',standalone=True)
 out=P/'assessment-hadi-headers.docx'
 with ZipFile(out,'w',ZIP_DEFLATED) as o:
  for k,v in parts.items():o.writestr(k,v)
