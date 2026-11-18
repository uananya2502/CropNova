from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).parent
A=ROOT/'assets'
A.mkdir(exist_ok=True)
font='/System/Library/Fonts/Supplemental/Times New Roman.ttf'
def f(n): return ImageFont.truetype(font,n)
# Figure 1: deliberately simple monochrome process diagram.
im=Image.new('RGB',(1600,390),'white'); draw=ImageDraw.Draw(im)
labels=[('Farm input','Season, soil, pH, water'),('Agent','Validate and coordinate'),('Knowledge and rules','Retrieve facts and check evidence'),('CSP solver','Test four requirements'),('Report','Explain each outcome')]
for i,(title,sub) in enumerate(labels):
    x=12+i*320
    draw.rectangle((x,85,x+294,260),outline='black',width=2)
    draw.text((x+147,120),title,font=f(30),fill='black',anchor='mm')
    # separate short subtitle lines
    words=sub.split(); lines=[' '.join(words[:3]),' '.join(words[3:])]
    for j,line in enumerate(lines): draw.text((x+147,175+j*32),line,font=f(24),fill='black',anchor='mm')
    if i<4:
        draw.line((x+295,170,x+317,170),fill='black',width=3)
        draw.polygon([(x+317,170),(x+308,164),(x+308,176)],fill='black')
draw.text((800,330),'The same reasoning pipeline processes each submitted profile',font=f(27),fill='black',anchor='mm')
im.save(A/'workflow.png')
# Figure 2: measured synthetic case outcomes, four candidates each.
im=Image.new('RGB',(1500,640),'white');draw=ImageDraw.Draw(im)
left=410;top=80;scale=190
for n in range(5):
    x=left+n*scale
    draw.line((x,top-15,x,500),fill='#dddddd',width=2)
    draw.text((x,535),str(n),font=f(28),fill='black',anchor='mm')
for i,(label,vals) in enumerate([('Matching profile',(2,2,0)),('Low water',(1,3,0)),('pH outside all ranges',(0,4,0)),('Season unknown',(0,2,2))]):
    y=90+i*100
    draw.text((385,y+24),label,font=f(30),fill='black',anchor='rm')
    x=left
    for count,shade in zip(vals,['#363636','#aaaaaa','#eeeeee']):
        if count:
            draw.rectangle((x,y,x+count*scale,y+50),fill=shade,outline='black',width=1)
            draw.text((x+count*scale/2,y+24),str(count),font=f(28),fill='white' if shade=='#363636' else 'black',anchor='mm')
            x+=count*scale
for i,(label,shade) in enumerate([('Feasible','#363636'),('Rejected','#aaaaaa'),('Unresolved','#eeeeee')]):
    x=420+i*290
    draw.rectangle((x,585,x+30,615),fill=shade,outline='black')
    draw.text((x+44,600),label,font=f(27),fill='black',anchor='lm')
im.save(A/'results.png')
# Current screenshot, converted for a restrained monochrome report.
shot=Image.open(A/'website.png')
shot.crop((0, 75, shot.width, min(495,shot.height))).convert('RGB').save(A/'website_bw.png')

d=Document();sec=d.sections[0]
sec.page_height=Inches(11.7);sec.page_width=Inches(8.3)
sec.top_margin=sec.bottom_margin=Inches(.72)
sec.left_margin=sec.right_margin=Inches(.82)
for name,size in [('Normal',11),('Title',25),('Subtitle',12),('Heading 1',15),('Heading 2',12),('Caption',9)]:
    st=d.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
    st.paragraph_format.space_after=Pt(7)
    rpr=st.element.get_or_add_rPr()
    rf=rpr.find(qn('w:rFonts'))
    if rf is None:
        rf=OxmlElement('w:rFonts');rpr.append(rf)
    for attr in list(rf.attrib):
        if 'Theme' in attr or 'theme' in attr: del rf.attrib[attr]
    for attr in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+attr),'Times New Roman')
    for borders in list(st.element.iter(qn('w:pBdr'))):borders.getparent().remove(borders)
    color=rpr.find(qn('w:color'))
    if color is not None:
        for attr in list(color.attrib):
            if 'theme' in attr.lower(): del color.attrib[attr]

for style in d.styles:
    for borders in list(style.element.iter(qn('w:pBdr'))):borders.getparent().remove(borders)
d.styles['Normal'].paragraph_format.line_spacing=1.12
for name in ['Heading 1','Heading 2']:
    d.styles[name].font.bold=True;d.styles[name].paragraph_format.space_before=Pt(11)
d.core_properties.title='CropNova Project Progress Report'
d.core_properties.author='CropNova Project Team'
d.core_properties.subject='Implementation progress and software evaluation'
foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=foot.add_run('CropNova  |  ');r.font.size=Pt(9)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');foot._p.append(fld)
def p(t,style=None):return d.add_paragraph(t,style)
def h(t):d.add_heading(t,1)
def caption(t):p(t,'Caption')
def pic(path,width):
    pp=d.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pp.add_run().add_picture(str(path),width=Inches(width))
def table(head,rows,widths):
    t=d.add_table(rows=1,cols=len(head));t.autofit=False
    for c,w in zip(t.columns,widths):c.width=Inches(w)
    for c,txt in zip(t.rows[0].cells,head):c.text=txt
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in rows:
        for c,txt in zip(t.add_row().cells,row):c.text=str(txt)
    for ri,row in enumerate(t.rows):
        for ci,c in enumerate(row.cells):
            c.width=Inches(widths[ci]);pr=c._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'5');el.set(qn('w:color'),'D9D9D9');borders.append(el)
            pr.append(borders)
            mar=OxmlElement('w:tcMar')
            for side in ['top','left','bottom','right']:
                e=OxmlElement('w:'+side);e.set(qn('w:w'),'95');e.set(qn('w:type'),'dxa');mar.append(e)
            pr.append(mar)
            if ri==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'EAEAEA');pr.append(sh)
            for pp in c.paragraphs:
                pp.paragraph_format.space_after=Pt(2);pp.paragraph_format.line_spacing=1.0
                for rr in pp.runs:rr.font.size=Pt(10);rr.bold=ri==0
    p('')
def page():d.add_page_break()

p('CropNova Project Progress Report','Title')
h('1 Project overview')
p('We have developed an integrated prototype that takes farm conditions, checks candidate crops and explains the outcome. The application now connects a browser interface, a structured knowledge base, a rule engine, a constraint solver and a reporting module. A user can follow the decision from the original inputs to the individual checks behind each crop result.')
p('The present version covers wheat, rice, maize and chickpea. It evaluates season, water availability, soil texture and soil pH. Our focus has been to make the reasoning visible and testable, including situations where a crop fails or the available information is insufficient.')
h('2 Work completed at a glance')
table(['Area','Current implementation'],[
('User interface','Farm profile form, four example profiles, crop comparison and detailed results'),
('Knowledge handling','JSON loading, structural validation, crop lookup and evidence filtering'),
('Intelligent agent','Input normalization, validation, module coordination and final status selection'),
('Rule engine','Crop knowledge and water evidence availability checks with rule traces'),
('CSP reasoning','Four hard constraints, deterministic search and three possible check states'),
('Verification','34 automated tests passing in the current local version')],[1.45,5.15])
p('For the presentation, we added 16 synthetic requirement records across the four crops. These exercise the actual reasoning code and are kept separate from the research knowledge base. They establish software behaviour, not agricultural validity.')
h('What this stage establishes')
p('The project has progressed beyond a form that merely displays entered values. It performs a repeatable assessment, distinguishes failure from missing evidence, and shows the reasons behind its output. Completing reviewed agricultural requirements is the next step toward useful field assessments.')


page();h('3 Planning phase')
p('Our project plan is built around one practical question: given a field profile, which of the available crops meet the conditions, and can we explain the answer? We kept the first version small enough to implement and inspect properly. The initial scope uses four crops and four hard checks.')
h('Defining the inputs and expected output')
p('We identified season, water availability, soil texture and measured pH as the active inputs for suitability checks. Location is used when checking fact applicability. The output separates feasible crops, rejected crops and unresolved crops. We also included clear messages for invalid input and missing knowledge, so the application can explain why it cannot decide.')
h('Choosing the AI approach')
p('We chose symbolic reasoning because the conditions can be written explicitly and checked one by one. A knowledge base stores requirements, rules check evidence conditions, and the CSP checks whether a crop satisfies the requirements. This gives us a reasoning process we can inspect without training a prediction model.')
h('Dividing the application into modules')
p('We separated the interface, agent, knowledge handling, rule engine, solver and explanations. Each module receives structured data and returns a structured result. This allows different parts of the project to be developed and tested without rebuilding the entire application.')
table(['Planning decision','How it appears in the implementation'],[
('Keep a manageable first scope','Four crops and four hard constraints'),
('Make every outcome explainable','Constraint reasons, fact IDs, source IDs and rule traces'),
('Handle incomplete information','Unknown checks and targeted follow-up questions'),
('Check the reasoning before wider use','Controlled profiles and automated expected-result tests'),
('Keep presentation data separate','Synthetic requirements and research knowledge use separate datasets')],[2.3,4.3])
h('Planning in the AI sense')
p('The agent follows a designed assessment sequence. It does not yet generate action plans for planting, irrigation or harvesting, and it does not implement a classical planning algorithm such as STRIPS. In this report, the planning phase means defining the problem, architecture, evidence requirements and evaluation cases.')

page();h('4 Literature review and related systems')
p('We reviewed three relevant examples to place CropNova in context. They represent environmental matching, irrigation decision support and explainable machine learning. The short review below draws on official product descriptions and a research paper abstract; it is not a systematic survey or a comparative performance experiment.')
h('FAO Ecocrop')
p('Ecocrop matches plant requirements with conditions entered by a user. Its official description includes climate and soil properties such as rainfall, soil texture, pH and fertility. It also provides a way to look up crop requirements and uses [1]. This is closely related to our problem of comparing a field profile with crop requirements.')
p('Relevance to CropNova: environmental matching is an established approach. Our current implementation narrows the scope to four checks and exposes the individual constraint outcomes. Ecocrop confirms that crop matching itself is not a new idea; our contribution is the implementation and presentation of an inspectable reasoning workflow.')
h('FAO CROPWAT')
p('CROPWAT calculates crop water and irrigation requirements from crop, soil and climate data. It also supports irrigation scheduling [2]. It therefore addresses water management at a much more detailed level than our low, moderate and high water categories.')
p('Relevance to CropNova: water needs require careful definitions and appropriate data. Our water check is an illustrative categorical constraint, not a substitute for a water-balance calculation or an irrigation schedule. CROPWAT points to a useful direction for future improvement.')
h('AgroXAI by Turgut Kok and Ozdemir')
p('The 2024 AgroXAI paper describes crop recommendations using weather and soil conditions, with explanations of machine-learning decisions through ELI5, LIME and SHAP. It also describes counterfactual alternative crop recommendations [3]. The abstract reports an edge-computing approach that combines ML and explainability.')
p('Relevance to CropNova: explanations are already an active research topic. CropNova produces explanations directly from explicit constraints and evidence references. This avoids a model-training step in our current design, but it does not establish higher recommendation accuracy than AgroXAI.')
h('Main lesson from the review')
p('Useful agricultural software needs both suitable data and understandable decisions. We have implemented the decision flow and traceability, while regional agricultural validation remains unfinished. The literature supports the direction of the project without justifying claims that CropNova is the first system of its kind.')

page();h('5 Project positioning and distinctive features')
p('CropNova is best described as a small, explainable crop-screening system built with symbolic AI. Its strength at this stage is the combination of visible constraint checks, evidence controls, uncertainty handling and a working browser interface. These are implemented design choices, not a claim of worldwide novelty.')
table(['System','Main approach','Relationship to CropNova'],[
('FAO Ecocrop [1]','Matches crop requirements with environmental conditions','Related matching problem; our first version exposes four explicit constraint results'),
('FAO CROPWAT [2]','Calculates crop water needs and irrigation requirements','More detailed water analysis; our categorical check has a narrower purpose'),
('AgroXAI [3]','ML recommendations with explanation methods','Related explainability goal; our decisions come from explicit constraints'),
('CropNova','Knowledge checks, evidence rules, CSP and deterministic explanations','Inspectable educational prototype with tested handling of failures and unknowns')],[1.25,2.3,3.05])
h('What makes our implementation worth presenting')
p('A user can see why a crop was rejected, rather than receiving only a crop name. The system keeps evidence identifiers attached to the checks and provides a separate view of rule outcomes. This makes it possible to connect a website result to the code and knowledge responsible for it.')
p('We also distinguish three situations that need different responses: a crop fails a requirement, the user has not supplied an input, or the knowledge base lacks suitable evidence. The presentation cases exercise these situations through the same agent and solver used by the application.')
h('References')
p('[1] Food and Agriculture Organization of the United Nations. Ecocrop. Official tool description. Accessed 21 October 2026. https://ecocrop.apps.fao.org/ecocrop/srv/en/home','Caption')
p('[2] Food and Agriculture Organization of the United Nations. CROPWAT. Official software description. Accessed 21 October 2026. https://www.fao.org/land-water/resources/tools/software/cropwat/en','Caption')
p('[3] Turgut, O., Kok, I., and Ozdemir, S. (2024). AgroXAI: Explainable AI-Driven Crop Recommendation System for Agriculture 4.0. arXiv:2412.16196. The arXiv record notes acceptance at IEEE BigData 2024. https://arxiv.org/abs/2412.16196','Caption')

page();h('6 How the system works')
p('The user submits a farm profile. The agent first cleans and validates it, loads the selected knowledge and evaluates the rules for each crop. It then sends candidates to the CSP solver and builds a report from the results.')
pic(A/'workflow.png',6.6);caption('Figure 1  Implemented assessment workflow')
h('The intelligent agent')
p('The agent is the coordinator. It normalizes values such as season names and numeric pH, checks supported inputs, loads knowledge and calls the reasoning modules. If information is missing, it asks a targeted question. If a module fails, it returns an explicit error instead of a successful assessment.')
h('Knowledge and rule evaluation')
p('Crop records are linked to facts and sources through IDs. Retrieval filters facts by verification status and source review. The current rules check whether usable crop knowledge and water-related evidence are available. Their results are visible on the page. A fired rule confirms an evidence condition; it does not by itself establish crop suitability.')
h('Constraint satisfaction and search')
p('We model the choice as a Constraint Satisfaction Problem, or CSP. The variable is selected_crop, the domain is the candidate list, and the constraints are the four crop requirements. The solver uses deterministic backtracking. With one variable, this means examining each crop in order and recording all four checks.')
table(['Check result','Meaning','Candidate decision'],[
('Satisfied','Evidence supports this requirement','Feasible only if all four checks pass'),
('Violated','At least one requirement does not match','Rejected'),
('Unknown','Input or suitable evidence is missing','Unresolved when there is no failure')],[1.1,2.8,2.7])
p('This version uses symbolic AI. We have not trained a machine-learning model, and explanations currently come from the computed trace rather than a language-model API.')

page();h('7 Website implementation')
p('The interface brings input, comparison and explanations into one flow. Example profiles let us show different outcomes without repeatedly filling the same fields. Additional context is grouped separately so the four active checks remain easy to identify.')
pic(A/'website_bw.png',5.2);caption('Figure 2  Current website showing the synthetic matching profile')
p('The comparison table gives a quick view of pass and fail results. Individual crop cards explain each constraint and retain evidence IDs. The expandable rule section shows why a rule fired or remained unknown. Users can refine their inputs and run the assessment again.')
p('Synthetic requirements are labelled on the page. The research dataset remains available separately, and the system reports insufficient knowledge when that dataset cannot support a complete decision.')


page();h('Reasoning shown on the website')
p('The screenshots below show the reasoning behind the matching profile. The rule engine records which evidence checks fired. The crop card then gives a separate explanation for each hard constraint, including the fact ID used. The requirements in this example are synthetic.')
# Keep both screenshots readable at their natural portrait proportions.
for source, target, crop in [('reasoning_rules.png','rules_bw.png',(15,390,530,795)),('reasoning_constraints.png','constraints_bw.png',(15,335,530,820))]:
    shot=Image.open(A/source)
    if crop: shot=shot.crop(crop)
    shot.convert('RGB').save(A/target)
t=d.add_table(rows=1,cols=2);t.autofit=False
for cell,filename in zip(t.rows[0].cells,['rules_bw.png','constraints_bw.png']):
    cell.width=Inches(3.25)
    cell.paragraphs[0].add_run().add_picture(str(A/filename),width=Inches(3.0))
caption('Figure 3  Expanded rule decisions and the four checks for wheat')
p('The rules establish evidence availability. Suitability is decided by the CSP: wheat passes the season, water, soil texture and pH checks in this example. Each explanation retains an evidence reference so that the result can be inspected in the knowledge records.')

page();h('8 Worked assessment and observed results')
p('We used Haryana as the example region, Rabi as the season, loamy soil, pH 7 and moderate water. All four crops were considered. Under the synthetic requirements, wheat and maize pass all four checks. Rice fails season, water and soil; chickpea fails soil texture.')
table(['Crop','Season','Water','Soil','pH','Outcome'],[
('Wheat','Pass','Pass','Pass','Pass','Feasible'),('Maize','Pass','Pass','Pass','Pass','Feasible'),('Rice','Fail','Fail','Fail','Pass','Rejected'),('Chickpea','Pass','Pass','Fail','Pass','Rejected')],[1.15,.8,.8,.8,.65,2.4])
p('We then changed one input at a time to observe whether the system responded consistently. With low water, only wheat remains feasible. With pH 9, every crop is rejected. With the season unknown, wheat and maize remain unresolved and the system asks for the growing season.')
pic(A/'results.png',6.5);caption('Figure 4  Actual synthetic case outcomes with four candidates per case')
p('These outcomes were generated by the local assessment pipeline. The chart counts crop classifications; it is not a model accuracy graph or evidence of farming success. Crop names are real, while the requirement values used here are synthetic.')
h('What the example demonstrates')
p('The assessment changes for an identifiable reason when an input changes. It does not always return a crop, and it does not treat missing measurements as passing evidence. This gives us a clear way to explain both the algorithm and its limits during assessment.')

page();h('9 Testing and implementation evidence')
p('The current local test run completed with 34 tests passing. Coverage includes the solver, agent, web interface, knowledge handling, rule engine and synthetic presentation cases. The suite checks expected outputs rather than relying only on the appearance of the website.')
table(['Test area','Tests','Examples covered'],[
('Agent and original web and CSP tests','15','Integration, invalid inputs, evidence preservation, feasible and rejected cases'),
('Knowledge base','9','Loading, lookup, verification filters and source-review checks'),
('Rule engine','7','Rule evaluation, evidence checks and trace information'),
('Presentation cases and routing','3','Four expected case outcomes, dataset separation and assessment route')],[2.15,.55,3.9])
p('Passing tests support the software behaviour covered by those cases. They do not independently verify agricultural facts or establish real-world recommendation accuracy.')
h('Where the work is implemented')
table(['Module','Responsibility'],[
('app.py','Form handling, comparison table, rule display and results page'),
('agent.py','Assessment coordination, validation and overall result status'),
('constraint_definitions.py and csp_solver.py','Four requirement checks and candidate search'),
('knowledge_base and rule_engine folders','Knowledge loading and filtering, rule evaluation and trace records'),
('explanations.py and demo.py','Trace-based explanations and isolated synthetic requirements')],[2.85,3.75])
h('10 Remaining work')
p('The immediate priority is to replace illustrative requirements with reviewed crop facts for a defined region, define water categories clearly and check agricultural cases independently. Preference-based ranking is a later extension.')
p('Generative AI integration is planned in the project synopsis. The assistant will turn ordinary language into a draft farm profile for user confirmation, explain the computed results, and answer questions using approved facts and sources. Rules and the CSP will continue to decide crop outcomes; GenAI must not change them or invent requirements.')
p('Before release, we need a provider adapter, citation and status checks, tests for unsupported answers and service failures, and a fallback to the existing template explanations. Live weather and market feeds remain outside the agreed scope.')
p('Verification command: python -m pytest -q. The application and tests were checked using Python 3.13. Runtime interface: http://127.0.0.1:8000/. Repository: github.com/uananya2502/CropNova.','Caption')
d.save(ROOT/'CropNova_Progress_Report.docx')
print(ROOT/'CropNova_Progress_Report.docx')
