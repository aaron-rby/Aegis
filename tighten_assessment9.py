from pathlib import Path
from docx import Document
from docx.shared import Pt
P=Path(__file__).parent
d=Document(P/'25BCE2640_ESA_Assessment_9_Final.docx')
active=False
heads={'Aim of the Experiment','Tools Required','Brief Theory','Circuit Connections','Arduino Code with Comments','Manual calculation:','Procedure','Output Snips','Result','Inference'}
for p in d.paragraphs:
    t=p.text.strip()
    if t=='Program 1':active=True
    if t=='ESA Lab Assessment report':active=False
    if not active:continue
    f=p.paragraph_format
    if t in heads:
        f.space_before=Pt(0);f.space_after=Pt(0);f.keep_with_next=True
        f.page_break_before=t=='Output Snips'
    elif t.startswith('Program '):
        f.space_before=Pt(0);f.space_after=Pt(3)
    elif p._p.xpath('.//w:drawing'):
        continue
    else:
        f.space_before=Pt(0);f.space_after=Pt(0)
        f.keep_with_next=False;f.keep_together=False
out=P/'25BCE2640_ESA_Assessment_9_Tight_Spacing.docx'
d.save(out);print(out)
