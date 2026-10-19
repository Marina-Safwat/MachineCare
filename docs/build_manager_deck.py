"""Build editable OOXML slides, notes, PDF and preview using local libraries only."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
from xml.etree import ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / 'manager-presentation-2026-10-19'
SLIDES = json.loads((OUT / 'slide-content.json').read_text(encoding='utf-8-sig'))
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = f'xmlns:a="{A}" xmlns:p="{P}" xmlns:r="{R}"'
GROUP = '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
COLOR_MAP = '<p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/>'

def rels(items):
    return '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="{i}" Type="{R}/{kind}" Target="{target}"/>' for i,kind,target in items) + '</Relationships>'

def wrap(text, size, width=860):
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if line and stringWidth(candidate,'Helvetica',size)>width:
                lines.append(line);line=word
            else:line=candidate
        lines.append(line)
    return lines

def box(ident, text, x,y,w,h,size,color,bold=False):
    paragraphs=''.join('<a:p><a:pPr><a:lnSpc><a:spcPct val="110000"/></a:lnSpc></a:pPr><a:r>'+
        f'<a:rPr lang="en-US" sz="{int(size*100)}" b="{int(bold)}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="Arial"/></a:rPr>'+
        f'<a:t>{escape(line)}</a:t></a:r><a:endParaRPr lang="en-US" sz="{int(size*100)}"/></a:p>' for line in text.split('\n'))
    return f'<p:sp><p:nvSpPr><p:cNvPr id="{ident}" name="Text {ident}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{int(x*12700)}" y="{int(y*12700)}"/><a:ext cx="{int(w*12700)}" cy="{int(h*12700)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" lIns="0" rIns="0" tIns="0" bIns="0"><a:noAutofit/></a:bodyPr><a:lstStyle/>{paragraphs}</p:txBody></p:sp>'

files={}
files['_rels/.rels']=rels([('rId1','officeDocument','ppt/presentation.xml')])
files['ppt/presentation.xml']=f'<p:presentation {NS}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:notesMasterIdLst><p:notesMasterId r:id="rId2"/></p:notesMasterIdLst><p:sldIdLst>'+''.join(f'<p:sldId id="{255+i}" r:id="rId{i+2}"/>' for i in range(1,len(SLIDES)+1))+'</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>'
files['ppt/_rels/presentation.xml.rels']=rels([('rId1','slideMaster','slideMasters/slideMaster1.xml'),('rId2','notesMaster','notesMasters/notesMaster1.xml')]+[(f'rId{i+2}','slide',f'slides/slide{i}.xml') for i in range(1,len(SLIDES)+1)])
files['ppt/slideMasters/slideMaster1.xml']=f'<p:sldMaster {NS}><p:cSld><p:spTree>{GROUP}</p:spTree></p:cSld>{COLOR_MAP}<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>'
files['ppt/slideMasters/_rels/slideMaster1.xml.rels']=rels([('rId1','slideLayout','../slideLayouts/slideLayout1.xml'),('rId2','theme','../theme/theme1.xml')])
files['ppt/slideLayouts/slideLayout1.xml']=f'<p:sldLayout {NS} type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>{GROUP}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
files['ppt/slideLayouts/_rels/slideLayout1.xml.rels']=rels([('rId1','slideMaster','../slideMasters/slideMaster1.xml')])
files['ppt/notesMasters/notesMaster1.xml']=f'<p:notesMaster {NS}><p:cSld><p:spTree>{GROUP}</p:spTree></p:cSld>{COLOR_MAP}<p:notesStyle/></p:notesMaster>'
files['ppt/notesMasters/_rels/notesMaster1.xml.rels']=rels([('rId1','theme','../theme/theme1.xml')])
colors={'dk1':'102238','lt1':'FFFFFF','dk2':'20374F','lt2':'EAF1F5','accent1':'29C6B7','accent2':'3A84D6','accent3':'F0B35C','accent4':'97AAC0','accent5':'6C83B5','accent6':'CB7596','hlink':'3A84D6','folHlink':'6C83B5'}
fills='<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'*3
lines=''.join('<a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>' for _ in range(3))
files['ppt/theme/theme1.xml']=f'<a:theme xmlns:a="{A}" name="MachineCare"><a:themeElements><a:clrScheme name="MachineCare">'+''.join(f'<a:{k}><a:srgbClr val="{v}"/></a:{k}>' for k,v in colors.items())+'</a:clrScheme><a:fontScheme name="Arial"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme><a:fmtScheme name="Standard"><a:fillStyleLst>'+fills+'</a:fillStyleLst><a:lnStyleLst>'+lines+'</a:lnStyleLst><a:effectStyleLst>'+('<a:effectStyle><a:effectLst/></a:effectStyle>'*3)+'</a:effectStyleLst><a:bgFillStyleLst>'+fills+'</a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>'
pdf=canvas.Canvas(str(OUT/'MachineCare_Manager_Review_2026-10-19.pdf'),pagesize=(960,540))
pdf.setTitle('MachineCare Manager Review | 19 October 2026')
notes=['# MachineCare speaker notes â€” 19 October 2026\n']
previews=[]
for i,slide in enumerate(SLIDES,1):
    size=20
    while len(wrap(slide['Body'],size))*size*1.1>310:size-=1
    assert size>=16,(i,size)
    body='\n'.join(wrap(slide['Body'],size))
    footer=f'MACHINECARE  /  LOCAL PILOT  /  19 OCT 2026                                          {i} / {len(SLIDES)}'
    specs=[(slide['Eyebrow'],48,30,864,26,12,'29C6B7',True),(slide['Title'],48,76,864,90,32,'FFFFFF',True),(body,48,174,864,310,size,'EAF1F5',False),(footer,48,510,864,18,10,'97AAC0',False)]
    shapes=''.join(box(j+2,*spec) for j,spec in enumerate(specs))
    files[f'ppt/slides/slide{i}.xml']=f'<p:sld {NS}><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="102238"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree>{GROUP}{shapes}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
    files[f'ppt/slides/_rels/slide{i}.xml.rels']=rels([('rId1','slideLayout','../slideLayouts/slideLayout1.xml'),('rId2','notesSlide',f'../notesSlides/notesSlide{i}.xml')])
    note=box(2,slide['Notes'],30,100,480,500,14,'102238').replace('<p:nvPr/>','<p:nvPr><p:ph type="body" idx="1"/></p:nvPr>',1)
    files[f'ppt/notesSlides/notesSlide{i}.xml']=f'<p:notes {NS}><p:cSld><p:spTree>{GROUP}{note}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>'
    files[f'ppt/notesSlides/_rels/notesSlide{i}.xml.rels']=rels([('rId1','notesMaster','../notesMasters/notesMaster1.xml'),('rId2','slide',f'../slides/slide{i}.xml')])
    pdf.setFillColorRGB(16/255,34/255,56/255);pdf.rect(0,0,960,540,fill=1,stroke=0)
    im=Image.new('RGB',(960,540),'#102238');draw=ImageDraw.Draw(im)
    for text,x,y,w,h,fs,color,bold in specs:
        pdf.setFillColorRGB(*(int(color[j:j+2],16)/255 for j in (0,2,4)))
        pdf.setFont('Helvetica-Bold' if bold else 'Helvetica',fs)
        font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',fs)
        for row,line in enumerate(text.split('\n')):
            pdf.drawString(x,540-y-fs-row*fs*1.1,line)
            draw.text((x,y+row*fs*1.1),line,font=font,fill='#'+color)
    im.save(OUT/f'slide-{i:02d}.png');previews.append(im)
    pdf.showPage();notes.append(f'## {i}. {slide["Title"]}\n\n{slide["Notes"]}\n')
pdf.save()
types={'presentation':'presentation','slideMaster':'slideMaster','slideLayout':'slideLayout','notesMaster':'notesMaster','notesSlide':'notesSlide','slide':'slide'}
ct='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
for name in files:
    if not name.endswith('.xml'):continue
    if '/theme/' in name:content='application/vnd.openxmlformats-officedocument.theme+xml'
    else:
        kind=next(k for k in types if Path(name).stem.startswith(k))
        content='application/vnd.openxmlformats-officedocument.presentationml.'+types[kind]+('.main+xml' if kind=='presentation' else '+xml')
    ct+=f'<Override PartName="/{name}" ContentType="{content}"/>'
files['[Content_Types].xml']=ct+'</Types>'
with ZipFile(OUT/'MachineCare_Manager_Review_2026-10-19.pptx','w',ZIP_DEFLATED) as archive:
    for name,xml in files.items():
        ET.fromstring(xml)
        archive.writestr(name,'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+xml)
(OUT/'SPEAKER_NOTES.md').write_text('\n'.join(notes),encoding='utf-8')
sheet=Image.new('RGB',(1440,1080),'white')
for n,im in enumerate(previews):sheet.paste(im.resize((480,270)),((n%3)*480,(n//3)*270))
sheet.save(OUT/'slide-overview.png')
print(f'Created {len(SLIDES)} editable slides with notes, PDF, previews and text notes. XML parsed successfully.')

