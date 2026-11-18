"""Build the beginner handbook from Markdown and the actual source-code locations.

Run from any directory: python3 scripts/build_learning_guide.py
The build is local and never reads API keys or private saved assessments.
"""
from __future__ import annotations

import ast
from collections import OrderedDict
import json
from pathlib import Path
import re
import textwrap
from xml.sax.saxutils import escape
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Preformatted, KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents

from agent import run_assessment
from public_profiles import REFERENCE_PROFILES

OUTPUT = ROOT / 'output/pdf/CropNova-Learning-and-Viva-Guide.pdf'
WIDTH = A4[0] - 40 * mm
BLACK, GRAY, PALE = colors.black, colors.HexColor('#666666'), colors.HexColor('#f3f3f3')
STYLES = {
    'body': ParagraphStyle('Body', fontName='Times-Roman', fontSize=11, leading=15.4, spaceAfter=8),
    'h1': ParagraphStyle('Chapter', fontName='Times-Bold', fontSize=21, leading=25, spaceAfter=16, keepWithNext=True),
    'h2': ParagraphStyle('Subheading', fontName='Times-Bold', fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=7, keepWithNext=True),
    'small': ParagraphStyle('Small', fontName='Helvetica', fontSize=8.2, leading=11.5, textColor=GRAY, spaceAfter=7),
    'bullet': ParagraphStyle('Bullet', fontName='Times-Roman', fontSize=10.7, leading=14.6, leftIndent=12, firstLineIndent=-10, spaceAfter=6),
    'code': ParagraphStyle('Code', fontName='Courier', fontSize=7.7, leading=10.5, backColor=PALE, borderPadding=8, spaceBefore=8, spaceAfter=12),
    'cell': ParagraphStyle('Cell', fontName='Helvetica', fontSize=8.4, leading=11.5, spaceAfter=0),
    'head': ParagraphStyle('Head', fontName='Helvetica-Bold', fontSize=8.4, leading=11.5, spaceAfter=0),
}


def ascii_text(text):
    """Keep built-in print fonts reliable without downloading any font files."""
    return str(text).translate(str.maketrans({'\u2013':'-','\u2014':'-','\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u00a0':' '}))


def inline(text):
    """Escape source text before allowing the two supported inline styles."""
    text=escape(ascii_text(text))
    text=re.sub(r'`([^`]+)`',r'<font name="Courier" size="9">\1</font>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    # Explicit HTTP(S) links only; never interpret arbitrary Markdown as HTML.
    text=re.sub(r'(https?://[^\s<>]+)',lambda m:'<link href="'+m.group(1)+'">'+m.group(1)+'</link>',text)
    return text


def paragraph(text, style='body'):
    return Paragraph(inline(text), STYLES[style])


def make_table(rows, widths=None):
    cells=[[paragraph(cell,'head' if index==0 else 'cell') for cell in row] for index,row in enumerate(rows)]
    table=Table(cells,colWidths=widths or [WIDTH/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),PALE),
        ('LINEBELOW',(0,0),(-1,0),.6,BLACK),('LINEBELOW',(0,1),(-1,-1),.25,colors.lightgrey),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
    ]))
    return table


def symbols(path):
    """Locate real definitions, including methods, without importing a module."""
    source=(ROOT/path).read_text()
    found={}
    def visit(nodes,prefix=''):
        for node in nodes:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                key=prefix+node.name
                found[key]=node
                if isinstance(node,ast.ClassDef):visit(node.body,key+'.')
    visit(ast.parse(source).body)
    return source,found


def code_excerpt(path,name):
    source,found=symbols(path)
    node=found[name]
    lines=source.splitlines()[node.lineno-1:node.end_lineno]
    if len(lines)>24:
        raise ValueError('Choose a smaller teaching excerpt: '+path+':'+name)
    printed=[]
    for number,line in enumerate(lines,node.lineno):
        parts=textwrap.wrap(line, width=87, replace_whitespace=False, drop_whitespace=False) or ['']
        printed.append(f'{number:>3}  '+parts[0])
        printed.extend('     '+part for part in parts[1:])
    return [paragraph(f'{path}:{node.lineno} - {name}()', 'small'),Preformatted(ascii_text('\n'.join(printed)),STYLES['code'])]


def arrow(drawing,x1,y1,x2,y2):
    drawing.add(Line(x1,y1,x2,y2,strokeWidth=.8))
    if x1==x2:
        step=4 if y2>y1 else -4
        points=[x2,y2,x2-3,y2-step,x2+3,y2-step]
    else:
        step=4 if x2>x1 else -4
        points=[x2,y2,x2-step,y2-3,x2-step,y2+3]
    drawing.add(Polygon(points,fillColor=BLACK,strokeColor=BLACK))


def box(drawing,x,y,width,label,sub=''):
    drawing.add(Rect(x,y,width,48,strokeWidth=.7,fillColor=colors.white))
    drawing.add(String(x+width/2,y+29,label,textAnchor='middle',fontName='Helvetica-Bold',fontSize=9))
    drawing.add(String(x+width/2,y+14,sub,textAnchor='middle',fontName='Helvetica',fontSize=7.5))


def figure(kind):
    if kind=='workflow':
        d=Drawing(WIDTH,205)
        w=(WIDTH-40)/3
        positions=[(0,145,'Field inputs','Browser form'),(w+20,145,'Validate','Consistent profile'),(2*(w+20),145,'Knowledge','Reviewed facts'),(2*(w+20),62,'Rules','Evidence / season'),(w+20,62,'CSP','Four crop checks'),(0,62,'Saved result','Reasons and sources')]
        for x,y,title,sub in positions:box(d,x,y,w,title,sub)
        arrow(d,w,169,w+20,169);arrow(d,2*w+20,169,2*(w+20),169)
        arrow(d,2*(w+20)+w/2,145,2*(w+20)+w/2,110)
        arrow(d,2*(w+20),86,2*w+20,86);arrow(d,w+20,86,w,86)
        d.add(String(0,24,'The webpage and PDF reuse the saved result. Optional language features explain it.',fontSize=8.3,fontName='Helvetica'))
        caption='Figure 1. The deterministic assessment path; arrows show data flow.'
    elif kind in {'rag','evidence'}:
        labels=([('Question','User wording'),('MiniLM','Retrieve notes'),('Evidence','Saved findings'),('Gemini','Write answer'),('Validation','Cited output')] if kind=='rag' else [('Input','Entered value'),('Check','Status + reason'),('Fact ID','Recorded value'),('Source ID','Published reference')])
        d=Drawing(WIDTH,98);w=(WIDTH-12*(len(labels)-1))/len(labels)
        for i,(title,sub) in enumerate(labels):
            x=i*(w+12);box(d,x,32,w,title,sub)
            if i<len(labels)-1:arrow(d,x+w,56,x+w+12,56)
        caption='Figure 3. Retrieve, write and validate; the saved crop decision is unchanged.' if kind=='rag' else 'Figure 2. A finding can be traced back to its recorded fact and source.'
    elif kind=='fuzzy':
        from fuzzy_logic import memberships
        d=Drawing(WIDTH,155)
        left,bottom,plot_w,plot_h=32,36,WIDTH-45,90
        d.add(Line(left,bottom,left+plot_w,bottom,strokeWidth=.7))
        d.add(Line(left,bottom,left,bottom+plot_h,strokeWidth=.7))
        for value in (0,.5,.8,1,1.2):
            x=left+value/1.2*plot_w
            d.add(String(x,bottom-14,str(value),fontName='Helvetica',fontSize=8,textAnchor='middle'))
        for value in (0,1):
            d.add(String(left-8,bottom+value*plot_h,str(value),fontName='Helvetica',fontSize=8,textAnchor='end'))
        for label,dash in [('low',None),('partial',[4,2]),('covered',[1,2])]:
            points=[]
            for i in range(121):
                value=i/100
                points.extend([left+value/1.2*plot_w,bottom+memberships(0,value)['water'][label]*plot_h])
            from reportlab.graphics.shapes import PolyLine
            d.add(PolyLine(points,strokeColor=BLACK,strokeWidth=1,strokeDashArray=dash))
        d.add(String(left,bottom+plot_h+14,'Low: solid    Partial: dashed    Covered: dotted',fontName='Helvetica',fontSize=8))
        d.add(String(left+plot_w/2,2,'Water budget / upper reference value',fontName='Helvetica',fontSize=8,textAnchor='middle'))
        caption='Fuzzy membership curves from the implemented functions. The vertical axis is membership (0-1).'
    elif kind=='checks':
        d=Drawing(WIDTH,108);w=(WIDTH-24)/3
        for i,(count,label,sub) in enumerate([('291','Automated tests','Software assertions'),('32','Planner comparisons','A* / uniform-cost search'),('6','Encoder smoke queries','Expected finding in top 3')]):
            x=i*(w+12);d.add(Rect(x,30,w,68,fillColor=colors.white,strokeWidth=.6))
            d.add(String(x+w/2,72,count,fontName='Times-Bold',fontSize=25,textAnchor='middle'))
            d.add(String(x+w/2,52,label,fontName='Helvetica-Bold',fontSize=8.5,textAnchor='middle'))
            d.add(String(x+w/2,39,sub,fontName='Helvetica',fontSize=7.4,textAnchor='middle'))
        caption='Figure 4. Separate review checks. These counts are not accuracy percentages.'
    else:raise ValueError(kind)
    return [d,paragraph(caption,'small')]


INDEX=OrderedDict([
('app.py', ['read_body','assess','assessment_request','answer_request','application','create_server']),
('profile_validation.py',['_number','normalize_profile','validate_profile']),
('agent.py',['_candidate_records','_select_candidates','_rule_adapter','_missing','_status','run_assessment']),
('knowledge_base/loader.py',['load_knowledge']),
('knowledge_base/validator.py',['validate_knowledge']),
('knowledge_base/retrieval.py',['get_usable_facts']),
('evidence.py',['scope_matches','numeric_range','assessment_facts']),
('rule_engine/rules.py',['get_rules','condition_has_crop','condition_has_water_evidence','condition_season_matches']),
('rule_engine/engine.py',['evaluate_rule','evaluate_rules']),
('constraint_definitions.py',['ConstraintOutcome','SeasonConstraint','WaterConstraint.check_numeric','SoilTextureConstraint','SoilPHConstraint']),
('csp_solver.py',['define_problem','solve_constraints']),
('fuzzy_logic.py',['memberships','infer_alignment','analyze_crop','analyze_assessment']),
('astar_search.py',['remaining_cost','search_plan','reconstruct']),
('preparation_planner.py',['follow_up_needs','available_actions','plan_assessment']),
('assessment_summary.py',['build_summary','explanation_for']),
('genai_explainer.py',['prepare_context','response_schema','validate_answer','generate_explanation']),
('gemini_provider.py',['call_gemini']),
('semantic_search.py',['load_encoder','assessment_documents','document_vectors','search_assessment']),
('assessment_questions.py',['validate_question','validate_written_answer','answer_question','cached_answer']),
('report_store.py',['save_report','load_report']),
('web_views.py',['farm_form','result_page','assessment_question_panel','condition_alignment_panel','preparation_plan_panel']),
('assessment_pdf.py',['create_pdf']),
])


def code_index():
    locations=[]
    rows=[[paragraph('Source file','head'),paragraph('Definition and starting line','head')]]
    for path,names in INDEX.items():
        _,found=symbols(path)
        locations.extend([[path,name,str(found[name].lineno)] for name in names])
        definitions='<br/>'.join(escape(name)+' - line '+str(found[name].lineno) for name in names)
        rows.append([paragraph(path,'cell'),Paragraph(definitions,STYLES['cell'])])
    (ROOT/'docs/code_locations.json').write_text(json.dumps(locations,indent=2)+'\n')
    table=Table(rows,colWidths=[WIDTH*.42,WIDTH*.58],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),PALE),
        ('LINEBELOW',(0,0),(-1,-1),.25,colors.lightgrey),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
    ]))
    return [table]


def source_index():
    seen={}
    for profile in REFERENCE_PROFILES.values():
        report=run_assessment(profile)
        for source in report.get('evidence',[]):seen[source['source_id']]=source
    output=[]
    for index,source in enumerate(seen.values(),1):
        output.append(paragraph(f'{index}. {source.get("title",source["source_id"])}','h2'))
        if source.get('section'):output.append(paragraph(source['section'],'small'))
        output.append(paragraph(source['url'],'small'))
    return output


class Handbook(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(str(path),pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=21*mm,bottomMargin=20*mm,title='CropNova - Learning and Viva Guide',author='CropNova Project',subject='Beginner explanation of the implemented code and AI concepts')
        self.addPageTemplates(PageTemplate(id='book',frames=[Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id='main',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.page_details))

    def page_details(self,canvas,doc):
        canvas.saveState()
        if doc.page>1:
            canvas.setFont('Helvetica',7.5);canvas.setFillColor(GRAY)
            canvas.drawString(20*mm,A4[1]-13*mm,'CROPNOVA / LEARNING AND VIVA GUIDE')
            canvas.setStrokeColor(colors.lightgrey);canvas.line(20*mm,16*mm,A4[0]-20*mm,16*mm)
            canvas.drawString(20*mm,11*mm,'Repository review: 14 November 2026')
            canvas.drawRightString(A4[0]-20*mm,11*mm,str(doc.page))
        canvas.restoreState()

    def afterFlowable(self,item):
        if isinstance(item,Paragraph) and item.style.name=='Chapter' and re.match(r'^\d+\.',item.getPlainText()):
            title=item.getPlainText();key='chapter-'+title.split('.')[0]
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(title,key,0,False)
            self.notify('TOCEntry',(0,title,self.page,key))


def parse_markdown(text):
    lines=text.splitlines();story=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('# '):
            story.extend([PageBreak(),paragraph(line[2:],'h1')]);i+=1
        elif line.startswith('## '):
            story.append(paragraph(line[3:],'h2'));i+=1
        elif line.startswith('```'):
            code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                code.extend(textwrap.wrap(ascii_text(lines[i]),width=92,replace_whitespace=False,drop_whitespace=False) or ['']);i+=1
            story.append(Preformatted('\n'.join(code),STYLES['code']));i+=1
        elif line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[cell.strip() for cell in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',cell) for cell in cells):rows.append(cells)
                i+=1
            widths=[WIDTH*.35,WIDTH*.65] if len(rows[0])==2 else None
            story.extend([make_table(rows,widths),Spacer(1,9)])
        elif line.startswith('[FIGURE:'):
            story.extend(figure(line[8:-1]));i+=1
        elif line.startswith('[CODE:'):
            path,name=line[6:-1].split(':',1);story.extend(code_excerpt(path,name));i+=1
        elif line=='[CODE_INDEX]':story.extend(code_index());i+=1
        elif line=='[AGRICULTURAL_SOURCES]':story.extend(source_index());i+=1
        elif line.startswith('- ') or re.match(r'^\d+\. ',line):
            story.append(paragraph(line if not line.startswith('- ') else '- '+line[2:],'bullet'));i+=1
        else:
            paragraph_lines=[line];i+=1
            while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','[','- ')):
                paragraph_lines.append(lines[i].strip());i+=1
            story.append(paragraph(' '.join(paragraph_lines)))
    return story


def main():
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    cover=[Spacer(1,50),paragraph('CROPNOVA / YOUR PERSONAL STUDY GUIDE','small'),
           Paragraph('A beginner\'s<br/>project handbook',ParagraphStyle('Cover',fontName='Times-Bold',fontSize=37,leading=43,spaceAfter=22)),
           Paragraph('Learn the ideas. Follow the code.<br/>Explain the decisions.',ParagraphStyle('Deck',fontName='Times-Roman',fontSize=18,leading=24,spaceAfter=28)),
           paragraph('Concepts, worked examples, code navigation and 50 viva questions.'),
           Spacer(1,22),make_table([['Inside this guide',''],['Understand','Knowledge, rules, CSP, fuzzy logic, A*, transformers and RAG.'],['Open the code','Actual function names, source extracts and generated line locations.'],['Practise','Positive, negative and uncertain cases; presentation and viva answers.']],[WIDTH*.26,WIDTH*.74]),
           Spacer(1,32),paragraph('Based on the implemented repository reviewed on 14 November 2026. Pretrained models are integrated; no new crop classifier or foundation model is claimed.','small'),
           paragraph('Local project: CropNova | Python 3.13 | Beginner edition','small'),PageBreak(),
           Paragraph('Contents',STYLES['h1']),paragraph('Read in order once. Use the linked contents and the final code index when revising. Code locations reflect this build.','small')]
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC',fontName='Times-Roman',fontSize=9.8,leading=12,spaceBefore=0,leftIndent=0,rightIndent=18)]
    story=cover+[toc]+parse_markdown((ROOT/'docs/learning_guide.md').read_text())
    Handbook(OUTPUT).multiBuild(story)
    print(OUTPUT)


if __name__=='__main__':main()
