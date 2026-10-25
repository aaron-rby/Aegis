from pathlib import Path
from pypdf import PdfReader,PdfWriter
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
P=Path(__file__).parent;out=P/'output'/'pdf';out.mkdir(parents=True,exist_ok=True)
sources=[('Ketan_25BCE2634',Path(r'C:\Users\aaron\Pictures\AI-Intrusion-Detection\ml\ASSESSMENT-8_25BCE2634_edited-LCD.pdf')),('Aaron_25BCE2640',Path(r'C:\Users\aaron\Downloads\25BCE2640 ESA LAB8 ASSESSMENTv4.pdf'))]
thumbs=[]
for name,path in sources:
    reader=PdfReader(path);groups={'color':[],'black-and-white':[]}
    for i,page in enumerate(reader.pages):
        photo=i!=0 and any(im.image.width>100 and im.image.height>100 for im in page.images)
        groups['color' if photo else 'black-and-white'].append(i)
    assert sorted(groups['color']+groups['black-and-white'])==list(range(len(reader.pages)))
    for kind,indices in groups.items():
        dest=out/f'{name}_{kind}.pdf';writer=PdfWriter()
        for i in indices:writer.add_page(reader.pages[i])
        writer.add_metadata({'/Title':f'{name} {kind} pages'})
        with dest.open('wb') as f:writer.write(f)
        check=PdfReader(dest);assert len(check.pages)==len(indices)
        for a,b in zip(indices,check.pages):
            assert reader.pages[a].get_contents().get_data()==b.get_contents().get_data()
        rendered=pdfium.PdfDocument(str(dest))
        for j in range(len(rendered)):
            # Render every extracted page to ensure it remains readable by a PDF renderer.
            image=rendered[j].render(scale=.45).to_pil().convert('RGB')
            if kind=='color' or j==0:
                image.thumbnail((230,300));tile=Image.new('RGB',(250,330),'white');tile.paste(image,((250-image.width)//2,25));ImageDraw.Draw(tile).text((8,6),f'{name} {kind} p{indices[j]+1}',fill='black');thumbs.append(tile)
        print(dest, 'pages:',len(indices),'original page numbers:',[i+1 for i in indices])
cols=4;rows=(len(thumbs)+cols-1)//cols
sheet=Image.new('RGB',(cols*250,rows*330),'#ddd')
for i,tile in enumerate(thumbs):sheet.paste(tile,((i%cols)*250,(i//cols)*330))
sheet.save(out/'split-verification.png')
