from pathlib import Path
import io
import pypdfium2 as pdfium
from pypdf import PdfReader,PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
P=Path(__file__).parent
src=Path(r'C:\Users\aaron\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions\08E4136ACFA46000013488ADB9F54F087BFB0CF1\transfers\2026-43\Ketan_25BCE2634_black-and-white.pdf')
title='Interfacing LED, Servo Motor, Ultrasonic Distance Sensor and LCD Hardware Using Arduino Uno'
d=pdfium.PdfDocument(str(src));removed=[]
for i in [0,20]:
 page=d[i];tp=page.get_textpage();targets=[]
 for obj in page.get_objects(textpage=tp):
  if isinstance(obj,pdfium.PdfTextObj):
   s=obj.extract().strip()
   if 'Peripheral Interfacing' in s or (i==0 and s in ['Assessment 8:','Arduino Uno']):targets.append(obj);removed.append((i+1,s))
 for obj in targets:page.remove_obj(obj)
 page.gen_content()
base=P/'ketan-title-base.pdf';d.save(str(base));d.close()
def wrap(text,font,size,width):
 lines=[];line=''
 for word in text.split():
  trial=(line+' '+word).strip()
  if line and stringWidth(trial,font,size)>width:lines.append(line);line=word
  else:line=trial
 if line:lines.append(line)
 return lines
def draw(c,text,x,y,width,font,size,leading,center=False):
 c.setFont(font,size)
 for line in wrap(text,font,size,width):
  if center:c.drawCentredString(x+width/2,y,line)
  else:c.drawString(x,y,line)
  y-=leading
reader=PdfReader(base);writer=PdfWriter()
for i,page in enumerate(reader.pages):
 if i in [0,20]:
  b=io.BytesIO();c=canvas.Canvas(b,pagesize=(float(page.mediabox.width),float(page.mediabox.height)))
  if i==0:
   draw(c,'Assessment 8: '+title,72,625,468,'Times-Roman',18,19,True)
   draw(c,title,152.5,348,388,'Times-Bold',11,12)
   draw(c,title,375,57,150,'Times-Roman',6.5,7)
  else:draw(c,'Title of Assessment: '+title,95.2,344,465,'Times-Bold',10.5,12)
  c.save();b.seek(0);page.merge_page(PdfReader(b).pages[0])
 writer.add_page(page)
out=P/'output'/'pdf'/'Ketan_25BCE2634_black-and-white_updated-title.pdf'
with out.open('wb') as f:writer.write(f)
check=PdfReader(out);assert len(check.pages)==22
assert 'Peripheral Interfacing' not in ''.join(p.extract_text() for p in check.pages)
print('Replaced title occurrences:',removed)
print(out)
render=pdfium.PdfDocument(str(out))
for i in [0,20]:render[i].render(scale=1.3).to_pil().save(P/f'ketan-title-updated-{i+1}.png')
