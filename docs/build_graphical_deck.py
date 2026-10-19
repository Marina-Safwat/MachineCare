"""Graphical manager deck: editable OOXML shapes/text plus genuine app captures."""
import json, math, posixpath
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).parent
OUT=ROOT/'manager-presentation-2026-10-19'/'graphical'
SHOTS=OUT/'screenshots'
OUT.mkdir(parents=True,exist_ok=True);SHOTS.mkdir(exist_ok=True)
W,H,S=960,540,2
NAVY='102238';INK='17344E';TEAL='007F80';MINT='33D2BB';BG='F3F7FA';GRAY='536B7D';WHITE='FFFFFF';AMBER='B06A09'
A='http://schemas.openxmlformats.org/drawingml/2006/main';P='http://schemas.openxmlformats.org/presentationml/2006/main';R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS=f'xmlns:a="{A}" xmlns:p="{P}" xmlns:r="{R}"'
GROUP='<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
def rels(items):return '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="{i}" Type="{R}/{k}" Target="{t}"/>' for i,k,t in items)+'</Relationships>'
def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',round(size*S))
def wrap(text,size,width,bold=False):
    result=[];f=font(size,bold)
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if line and f.getlength(candidate)>width*S:result.append(line);line=word
            else:line=candidate
        result.append(line)
    return result
def color(c):return tuple(int(c[i:i+2],16)/255 for i in (0,2,4))

pdf=canvas.Canvas(str(OUT/'MachineCare_Graphical_Manager_Review.pdf'),pagesize=(W,H))
pdf.setTitle('MachineCare | Graphical Manager Review | 19 October 2026')
slides=[];media={};missing=[]
class Slide:
    def __init__(self,title,section,notes,dark=False):
        self.title,self.notes,self.dark=title,notes,dark;self.xml=[];self.rels=[];self.id=1
        self.im=Image.new('RGB',(W*S,H*S),'#'+(NAVY if dark else BG));self.draw=ImageDraw.Draw(self.im)
        pdf.setFillColorRGB(*color(NAVY if dark else BG));pdf.rect(0,0,W,H,fill=1,stroke=0)
        self.text(section.upper(),36,22,880,11,MINT if dark else TEAL,True)
        self.text(title,36,54,888,29,WHITE if dark else INK,True,maxh=74)
    def ident(self):self.id+=1;return self.id
    def rect(self,x,y,w,h,fill,radius=True):
        ident=self.ident();geom='roundRect' if radius else 'rect'
        self.xml.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{ident}" name="Panel {ident}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{int(x*12700)}" y="{int(y*12700)}"/><a:ext cx="{int(w*12700)}" cy="{int(h*12700)}"/></a:xfrm><a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>')
        self.draw.rounded_rectangle((x*S,y*S,(x+w)*S,(y+h)*S),radius=12*S if radius else 0,fill='#'+fill)
        pdf.setFillColorRGB(*color(fill));pdf.roundRect(x,H-y-h,w,h,12 if radius else 0,fill=1,stroke=0)
    def text(self,text,x,y,w,size=18,fill=INK,bold=False,maxh=None):
        lines=wrap(text,size,w,bold);height=len(lines)*size*1.18+3
        assert not maxh or height<=maxh,(self.title,text,height,maxh)
        assert y+height<=H-10,(self.title,text,'bottom overflow')
        ident=self.ident();pars=''
        for n,line in enumerate(lines):
            pars+=f'<a:p><a:pPr><a:lnSpc><a:spcPct val="118000"/></a:lnSpc></a:pPr><a:r><a:rPr lang="en-US" sz="{int(size*100)}" b="{int(bold)}"><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill><a:latin typeface="Arial"/></a:rPr><a:t>{escape(line)}</a:t></a:r><a:endParaRPr sz="{int(size*100)}"/></a:p>'
            self.draw.text((x*S,(y+n*size*1.18)*S),line,font=font(size,bold),fill='#'+fill)
            pdf.setFillColorRGB(*color(fill));pdf.setFont('Helvetica-Bold' if bold else 'Helvetica',size);pdf.drawString(x,H-y-size-n*size*1.18,line)
        self.xml.append(f'<p:sp><p:nvSpPr><p:cNvPr id="{ident}" name="Text {ident}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{int(x*12700)}" y="{int(y*12700)}"/><a:ext cx="{int(w*12700)}" cy="{int((height+5)*12700)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" lIns="0" rIns="0" tIns="0" bIns="0"><a:noAutofit/></a:bodyPr><a:lstStyle/>{pars}</p:txBody></p:sp>')
    def image(self,path,x,y,w,h):
        path=Path(path)
        if not path.exists():missing.append(path.name);self.rect(x,y,w,h,'E1EAF0');self.text('Screenshot capture pending',x+15,y+25,w-30,17);return
        im=Image.open(path).convert('RGB');ratio=min(w/im.width,h/im.height);iw,ih=im.width*ratio,im.height*ratio;x+=(w-iw)/2;y+=(h-ih)/2
        name='image'+str(len(media)+1)+'.png';media[name]=path.read_bytes();rid='rId'+str(len(self.rels)+3);self.rels.append((rid,'image','../media/'+name));ident=self.ident()
        self.xml.append(f'<p:pic><p:nvPicPr><p:cNvPr id="{ident}" name="App screenshot"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="{int(x*12700)}" y="{int(y*12700)}"/><a:ext cx="{int(iw*12700)}" cy="{int(ih*12700)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')
        self.im.paste(im.resize((round(iw*S),round(ih*S)),Image.Resampling.LANCZOS),(round(x*S),round(y*S)))
        pdf.drawImage(ImageReader(im),x,H-y-ih,iw,ih)
    def card(self,x,y,w,h,title,body,accent=TEAL):
        self.rect(x,y,w,h,WHITE);self.rect(x,y,5,h,accent,False)
        self.text(title,x+18,y+16,w-36,18,accent,True,maxh=55)
        self.text(body,x+18,y+76,w-36,15,GRAY,maxh=h-84)
    def end(self):
        index=len(slides)+1
        self.text('MACHINECARE  |  LOCAL PILOT  |  19 OCT 2026',36,515,760,9,'AABECF' if self.dark else GRAY)
        self.text(f'{index:02d}',890,508,40,12,MINT if self.dark else TEAL,True)
        self.im.save(OUT/f'slide-{index:02d}.png');pdf.showPage();slides.append(self)

def screenshot(title,section,shot,headline,points,notes):
    s=Slide(title,section,notes);s.rect(36,132,554,365,WHITE);s.image(SHOTS/(shot+'.png'),44,140,538,349)
    s.text(headline,618,145,300,24,TEAL,True,maxh=90)
    y=250
    for n,p in enumerate(points,1):
        s.rect(618,y,26,26,TEAL);s.text(str(n),626,y+3,20,14,WHITE,True);s.text(p,655,y,260,16,INK,maxh=68);y+=77
    s.end()

s=Slide('MachineCare','Manager proposal','Open with the product and the purpose. Screenshots are captured from the existing app using the local demonstration database. Operational values remain illustrative.',True)
s.text('Equipment. Parts.\nEvery replacement.',40,145,420,38,WHITE,True,maxh=150)
s.text('A shared view for maintenance teams\nDIMM presses + AOI robot cells',42,312,400,20,'BED2E2')
s.rect(40,413,390,54,TEAL);s.text('Proposal: one-line validation pilot',56,428,360,18,WHITE,True)
s.image(SHOTS/'overview.png',480,126,440,365);s.end()

s=Slide('A connected maintenance record','01 / Why this matters','These are intended workflow benefits, not measured ROI. The pilot should measure traceability, stock accuracy and operator usability.')
for i,(t,b) in enumerate([('Know the equipment','Find the machine, line and compatible component.'),('Know the stock','See physical, reserved and available quantities.'),('Know the history','Connect completion to the person, part and cost snapshot.')]):s.card(36+i*300,145,282,265,t,b)
s.rect(36,438,888,48,NAVY);s.text('ONE WORKFLOW     Request  >  Review  >  Reserve  >  Complete  >  Trace',54,452,850,18,WHITE,True);s.end()

s=Slide('Two DIMM presses + one AOI on every line','02 / Production model','There are three configured lines, not a complete survey of all nine building records. Existing ACOS and conveyor are retained. New asset identifiers and statuses are demo placeholders.')
for row,label in enumerate(['B01 / L01','B01 / L02','B03 / L02']):
 y=145+row*94;s.rect(36,y,166,74,NAVY);s.text(label,54,y+23,140,20,WHITE,True)
 for j,name in enumerate(['DIMM 1','DIMM 2','AOI / TM robot']):
  x=224+j*233;s.rect(x,y,213,74,TEAL if j<2 else '355F8A');s.text(name,x+20,y+24,185,19,WHITE,True)
s.text('6 DIMMs + 3 AOIs + existing ACOS & conveyor = 11 equipment records',40,453,880,20,TEAL,True);s.end()

s=Slide('Three roles, clear operational boundaries','03 / Ownership','Backend role and line/building scope checks enforce these distinctions. Shared inventory is facility-wide; maintenance access is scoped.')
for i,(t,b) in enumerate([('Administrator','Accounts and access\nBuildings and lines\nSystem administration\nOperational work'),('Lead','Assigned equipment\nCatalog and stock\nReview and completion\nPurchasing and audit'),('Technician','Assigned machines\nReplacement requests\nOwn approved completion\nScoped history')]):s.card(36+i*300,142,282,328,t,b)
s.end()
screenshot('The overview puts priorities in one place','04 / App tour','overview','Start with the exceptions',['Equipment status and stock alerts','Pending work and purchasing visibility','Recent replacements with traceability'],'Actual app capture. Counters and costs reflect the demo snapshot; not production performance metrics.')
screenshot('Find the line, then the machine','05 / Equipment','equipment','Navigate the plant structure',['Building > line > station > machine','DIMM and AOI compatibility','Search and scope-aware access'],'Actual Equipment screen. New machine tags/stations/statuses are demo placeholders. Preserve existing asset history.')
screenshot('A real DIMM component in shared inventory','06 / Inventory','inventory_dimm','Finger cylinder / HFD12X50',['Airtac model supplied by maintenance','4 installed per DIMM press','Demo stock is separate from installed quantity'],'The supplied model and installed count are real references. Opening stock of eight was illustrative; current balances may differ after demo actions.')
screenshot('AOI references are now part of the catalog','07 / AOI','inventory_aoi','PILZ / robot-cell components',['7 AOI component entries','Exact supplied models and serial references','Two illustrative spare units per entry'],'AOI robot, PLC, supply and box counts of one were confirmed by the user. Do not treat these catalog entries as a safety-system inspection or certification.')
s=Slide('Installed quantities are not spare inventory','08 / Data meaning','Example uses initial demo stock. Four finger cylinders per DIMM multiplied by two DIMMs means eight installed on one line. Shared spares are a distinct balance and are not multiplied by line count.')
s.rect(36,145,420,290,NAVY);s.text('ON ONE LINE',58,169,370,13,MINT,True);s.text('4  x  2  =  8',58,222,370,42,WHITE,True);s.text('Finger cylinders installed\n4 per DIMM / 2 DIMMs',58,318,370,21,WHITE)
s.rect(480,145,444,290,WHITE);s.text('IN SHARED STORES',504,169,390,13,TEAL,True);s.text('8 demo spares',504,222,390,35,TEAL,True);s.text('Illustrative opening balance\nVerify with a physical count',504,318,390,21,GRAY);s.end()

s=Slide('From request to an auditable replacement','09 / Maintenance flow','Pending early work reserves nothing. Approval reserves stock; completion deducts stock once and creates history. Manager early work requires an explanation and records immediate confirmation.')
steps=[('01','Request','Machine + compatible part'),('02','Review','Early work needs explanation'),('03','Reserve','Approval holds availability'),('04','Complete','Confirm physical work'),('05','Record','Ledger + history snapshots')]
for i,(n,t,b) in enumerate(steps):
 x=36+i*180;s.rect(x,164,167,235,WHITE);s.text(n,x+15,181,140,36,TEAL,True);s.text(t,x+15,241,140,20,INK,True);s.text(b,x+15,294,138,15,GRAY)
s.rect(36,433,888,52,NAVY);s.text('APPROVAL reserves stock. Only COMPLETION deducts physical inventory.',53,450,850,18,WHITE,True);s.end()
screenshot('Review work before recording completion','10 / Approvals','approvals','Visibility before deduction',['Pending versus approved work','Early-work explanations and review','Completion and cancellation controls'],'Actual app screen. Any rehearsal records are fictional and confined to the demo database. Empty queues are valid; no screenshot is fabricated.')
screenshot('History keeps the replacement context','11 / Traceability','history','A record you can explain',['Who completed the work and when','Part, quantity and captured location','Historical cost snapshot retained'],'Actual history capture. Existing sample maintenance and unknown-price catalog entries do not establish real operating cost.')
screenshot('Purchasing connects shortages to receipts','12 / Purchasing','reorders','Ordering is not receiving',['Lead requests start approved','Track orders and partial deliveries','Only receipts add physical stock'],'Administrator requests require another manager review. Supplier ordering remains manual; no order is transmitted by this presentation.')
screenshot('Reports make the records usable','13 / Reporting','reports','From operational view to CSV',['Maintenance outlook and repeated early work','Inventory, purchasing and history exports','Role-based visibility and filters'],'Actual report screen. CSV generation exists; final Chrome download and Excel opening remain manual acceptance checks unless separately verified. Cost reports remain incomplete with placeholder prices.')
screenshot('Stock movements remain explainable','14 / Stock ledger','ledger','Every movement has context',['Opening balances, receipts and adjustments','Completion deductions','Actor, reason and running balance'],'Actual stock movement screen. Imported opening stock is explicitly labeled illustrative. No manager approval should rely on fictional inventory.')

s=Slide('Be precise about what the data tells us','15 / Confidence','Do not mix confirmed component references with planning or asset assumptions. This separation is visible in the app and must remain in the presentation.')
s.card(36,145,282,320,'SUPPLIED / CONFIRMED','Names and stated makers\nModel / serial references\nInstalled component counts\n2 DIMMs + 1 AOI per line',TEAL)
s.card(339,145,282,320,'ILLUSTRATIVE','Spare stock and targets\nNew tags and stations\nNew operating statuses\nDemo replacement intervals','355F8A')
s.card(642,145,282,320,'STILL TO VERIFY','Actual bins and prices\nSuppliers and lead times\nNameplate spellings\nPhysical inventory',AMBER);s.end()

s=Slide('Working pilot; integrations need activation','16 / Architecture','Flutter web, Python standard-library HTTP API and SQLite are the current architecture. No framework replacement or company-network exposure has been approved. Email and scheduled operations are not activated.')
for x,t,b in [(36,'Flutter web','Operator / Lead / Admin'),(339,'Local API','Permissions + transactions'),(642,'SQLite','Inventory + history + audit')]:s.card(x,142,282,208,t,b)
s.rect(36,382,432,100,NAVY);s.text('AVAILABLE CODE',54,399,390,13,MINT,True);s.text('Backups / alerts / optional TLS email',54,431,390,18,WHITE)
s.rect(490,382,434,100,'FBEBD4');s.text('NOT AN ACTIVATED SERVICE',508,399,390,13,AMBER,True);s.text('Needs configuration, owners and testing',508,431,390,18,INK);s.end()

s=Slide('Six gates before production deployment','17 / Production readiness','These are acceptance gates, not a promise of a production date. IT, maintenance and engineering must assign owners and accept evidence. Independent security review remains required.')
gates=[('01 / DATA','Validate assets, stock, bins, prices and intervals.'),('02 / HOSTING','Approved server, HTTPS and deployment model.'),('03 / SECURITY','Identity, access controls, secrets and review.'),('04 / RECOVERY','Protected off-host backups and restore drill.'),('05 / OPERATIONS','Monitored services, patching and support.'),('06 / ACCEPTANCE','Browser roles, exports, load and user sign-off.')]
for i,(t,b) in enumerate(gates):s.card(36+(i%3)*300,140+(i//3)*180,282,162,t,b,TEAL if i<3 else '355F8A')
s.end()
s=Slide('Agree the rules before adding complexity','18 / Open workflow decisions','These items have not been implemented speculatively. A limited release may explicitly defer them; otherwise agree rules and test their effects on history, stock and approvals.')
for i,(t,b) in enumerate([('Multi-bin stock','Allocation, transfers and reservation location.'),('Backdated work','Allowed dates, time zones and interval effects.'),('Emergency work','Override roles, limits and review deadline.'),('Corrections','Approval and reversal of stock/history effects.')]):s.card(36+(i%2)*452,140+(i//2)*178,436,162,t,b)
s.end()
s=Slide('A staged path from demo to adoption','19 / Proposed rollout','No calendar promises. Advance when each stage meets agreed acceptance criteria. Suggested pilot measures: traceability, stock accuracy and operator usability.')
for i,(t,b) in enumerate([('NOW','Graphical demonstration\nReview the workflow'),('NEXT','Validate one line\nReconcile real inventory'),('THEN','IT + security gates\nRole-based acceptance'),('RELEASE','Owner sign-off\nMonitored operation')]):s.card(36+i*225,153,209,287,t,b,TEAL if i<2 else '355F8A')
s.end()
s=Slide('Approve a focused validation pilot','20 / Manager decision','Ask for a supervised pilot, a maintenance data owner, and an IT/security reviewer. Agree success measures before promising savings or a production launch date.',True)
for i,(n,t) in enumerate([('1','Choose one validated line'),('2','Name maintenance and IT owners'),('3','Agree acceptance measures')]):
 y=150+i*98;s.rect(40,y,60,60,TEAL);s.text(n,61,y+11,35,29,WHITE,True);s.text(t,122,y+13,760,25,WHITE,True)
s.text('A working local pilot today. A controlled release after validation.',42,464,880,19,'BED2E2');s.end()

def table_slide(title,headers,rows,widths,notes):
    s=Slide(title,'Appendix / component reference',notes);x0,y0=36,135
    s.rect(x0,y0,888,35,NAVY,False);x=x0
    for h,w in zip(headers,widths):s.text(h,x+8,y0+8,w-16,13,WHITE,True);x+=w
    for row,values in enumerate(rows):
        y=y0+35+row*30;s.rect(x0,y,888,30,WHITE if row%2==0 else 'E4EDF3',False);x=x0
        for value,w in zip(values,widths):s.text(str(value),x+8,y+7,w-16,12,INK,maxh=26);x+=w
    s.end()
table_slide('DIMM component reference', ['Component','Manufacturer','Supplied identifier','Per DIMM'],[
('Load cell','Delta Transducers','Serial 2511231',5),('Finger cylinder','Airtac','HFD12X50',4),('Vertical cylinder','Airtac','HLQ12X50S',5),('Solenoid valve','Airtac','7V110-6',10),('Tray cylinder','Airtac','TCL25X20S',2),('Tray clamp cylinder','Unknown','HLS16X20SAS',4),('Finger reed switch','Airtac','DMSH A11DW',8),('Vertical reed switch','Airtac','D-M98W',10),('Flag sensor','Panasonic','PM-T45',8),('Photoelectric sensor','Panasonic','CX-441',12)],[230,195,330,133],'Exact supplied references. Load-cell serial is not a general part number. The tray clamp manufacturer remains unknown. Spare quantities are separate.')
table_slide('AOI component reference',['Component','Manufacturer','Supplied identifier','Per AOI'],[
('TM robot','TM (as supplied)','Model not supplied',1),('Small light curtain','PILZ','PSEN op113H-s-30-030',4),('Large light curtain','PILZ','PESN op113H-s-30-075',2),('PLC PNOZ m bo.1','PILZ','Ident-772104',1),('Tower light','Unknown','ASTLF-110-4-5FT-CM',2),('Switching power supply','Unknown','s-120-24',1),('Control box','VEVOR','Serial 240108586510146',1)],[230,175,350,133],'Identifiers retained exactly as supplied. User confirmed one robot, PLC, supply and control box. Verify nameplates. No safety-function certification is implied.')

pdf.save()
base=ROOT/'manager-presentation-2026-10-19'/'MachineCare_Manager_Review_2026-10-19.pptx'
with ZipFile(base) as archive:
    files={n:archive.read(n) for n in archive.namelist() if n.startswith(('ppt/theme/','ppt/slideMasters/','ppt/slideLayouts/','ppt/notesMasters/'))}
files['_rels/.rels']=rels([('rId1','officeDocument','ppt/presentation.xml')])
files['ppt/presentation.xml']=f'<p:presentation {NS}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:notesMasterIdLst><p:notesMasterId r:id="rId2"/></p:notesMasterIdLst><p:sldIdLst>'+''.join(f'<p:sldId id="{255+i}" r:id="rId{i+2}"/>' for i in range(1,len(slides)+1))+'</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>'
files['ppt/_rels/presentation.xml.rels']=rels([('rId1','slideMaster','slideMasters/slideMaster1.xml'),('rId2','notesMaster','notesMasters/notesMaster1.xml')]+[(f'rId{i+2}','slide',f'slides/slide{i}.xml') for i in range(1,len(slides)+1)])
for i,s in enumerate(slides,1):
    bg=NAVY if s.dark else BG
    files[f'ppt/slides/slide{i}.xml']=f'<p:sld {NS}><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree>{GROUP}{"".join(s.xml)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
    files[f'ppt/slides/_rels/slide{i}.xml.rels']=rels([('rId1','slideLayout','../slideLayouts/slideLayout1.xml'),('rId2','notesSlide',f'../notesSlides/notesSlide{i}.xml')]+s.rels)
    files[f'ppt/notesSlides/notesSlide{i}.xml']=f'<p:notes {NS}><p:cSld><p:spTree>{GROUP}<p:sp><p:nvSpPr><p:cNvPr id="2" name="Notes"/><p:cNvSpPr txBox="1"/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>{escape(s.notes)}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>'
    files[f'ppt/notesSlides/_rels/notesSlide{i}.xml.rels']=rels([('rId1','notesMaster','../notesMasters/notesMaster1.xml'),('rId2','slide',f'../slides/slide{i}.xml')])
for name,data in media.items():files['ppt/media/'+name]=data
ct='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
for n in files:
    if not n.endswith('.xml'):continue
    if '/theme/' in n:ctype='application/vnd.openxmlformats-officedocument.theme+xml'
    else:
        kind=next(k for k in ['presentation','slideMaster','slideLayout','notesMaster','notesSlide','slide'] if Path(n).stem.startswith(k))
        ctype='application/vnd.openxmlformats-officedocument.presentationml.'+kind+('.main+xml' if kind=='presentation' else '+xml')
    ct+=f'<Override PartName="/{n}" ContentType="{ctype}"/>'
files['[Content_Types].xml']=ct+'</Types>'
for n,data in files.items():
    if n.endswith(('.xml','.rels')):
        el=ET.fromstring(data)
        if n.endswith('.rels'):
            folder='' if n=='_rels/.rels' else posixpath.dirname(posixpath.dirname(n))
            for r in el:assert posixpath.normpath(posixpath.join(folder,r.attrib['Target'])) in files
with ZipFile(OUT/'MachineCare_Graphical_Manager_Review.pptx','w',ZIP_DEFLATED) as z:
    for n,data in files.items():z.writestr(n,data)
(OUT/'SPEAKER_NOTES.md').write_text('\n\n'.join(f'## {i}. {s.title}\n\n{s.notes}' for i,s in enumerate(slides,1)),encoding='utf-8')
sheet=Image.new('RGB',(1440,math.ceil(len(slides)/3)*270),'white')
for i,s in enumerate(slides):sheet.paste(s.im.resize((480,270)),((i%3)*480,(i//3)*270))
sheet.save(OUT/'slide-overview.png')
(OUT/'validation.json').write_text(json.dumps({'slides':len(slides),'embedded_screenshot_uses':len(media),'missing_screenshots':missing,'xml_and_relationships':'passed','renderer':'PIL/PDF from same slide specification; not desktop PowerPoint'},indent=2))
print(f'{len(slides)} slides; {len(media)} screenshot uses; missing: {missing}')
