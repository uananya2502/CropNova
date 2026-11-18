"""Public-site behaviour, explainability and personalised report integrity."""
from copy import deepcopy
from io import BytesIO
import json
import re
from unittest.mock import patch
from urllib.parse import urlencode
from pypdf import PdfReader
import pytest
from app import application, assess
from assessment_pdf import create_pdf
from assessment_summary import build_summary
from public_profiles import REFERENCE_PROFILES
from report_store import save_report, load_report
from tests.test_genai import valid_answer
from genai_explainer import prepare_context


@pytest.fixture(autouse=True)
def private_reports(tmp_path,monkeypatch):
    monkeypatch.setattr('report_store.DATABASE_PATH',tmp_path/'private'/'reports.sqlite3')


def response(method='GET',path='/',data=None,query=''):
    body=urlencode(data or {},doseq=True).encode()
    result={}
    def start(status,headers):result.update(status=status,headers=dict(headers))
    environ={'REQUEST_METHOD':method,'PATH_INFO':path,'QUERY_STRING':query,'CONTENT_LENGTH':str(len(body)),'wsgi.input':BytesIO(body)}
    result['body']=b''.join(application(environ,start))
    return result


def saved_assessment(**updates):
    result=response('POST','/assess',{**REFERENCE_PROFILES['reference-wheat'],**updates})
    assert result['status']=='303 See Other'
    location=result['headers']['Location']
    token=location.rsplit('/',1)[-1]
    return token,load_report(token),response(path=location)


def test_home_is_blank_and_has_no_synthetic_or_engine_language():
    html=response()['body'].decode()
    for word in ['synthetic','CSP','rule engine','prototype','backtracking','classroom']:
        assert word.lower() not in html.lower()
    assert 'value="Haryana"' not in html
    assert 'Assess my field' in html
    assert 'crop names are real' not in html.lower()


def test_stale_fixture_parameters_cannot_activate_synthetic_data():
    result=response('POST','/report',{**REFERENCE_PROFILES['reference-wheat'],'mode':'demo'})
    report=json.loads(result['body'])
    assert report['dataset_kind']=='research'
    assert 'SYNTHETIC_SOURCE' not in str(report)
    html=response(query='preset=match')['body'].decode()
    assert 'Synthetic' not in html
    assert 'value="Haryana"' not in html


def test_published_examples_stay_available_when_explicitly_requested():
    redirect=response(query='preset=reference-wheat')
    assert redirect['status']=='302 Found'
    assert redirect['headers']['Location']=='/assess?preset=reference-wheat'
    html=response(path='/assess',query='preset=reference-wheat')['body'].decode()
    assert 'value="Haryana"' in html
    assert 'value="650"' in html


def test_result_shows_inputs_references_reasons_and_source_links():
    _,report,result=saved_assessment()
    html=result['body'].decode()
    for phrase in ['Your entry','Published reference','Soil pH','650 mm','450–650','sources','Matches checked conditions']:
        assert phrase in html
    for word in ['CONSTRAINT001','FACT_WHEAT','FEASIBLE_OPTIONS_FOUND','CSP','synthetic']:
        assert word not in html
    assert report['status']=='FEASIBLE_OPTIONS_FOUND'
    assert 'haryanaseeds.org.in' in html
    assert 'www.fao.org' in html


def test_saved_result_and_download_do_not_call_ai_again():
    with patch('app.generate_explanation',side_effect=lambda report,requested: {'status':'generated','explanations':valid_answer(prepare_context(report))['explanations']} ) as model:
        token,report,result=saved_assessment(use_genai='yes')
        response(path='/assessment/'+token)
        pdf=response(path='/reports/'+token+'.pdf')
    assert model.call_count==1
    assert pdf['status']=='200 OK'
    assert pdf['headers']['Content-Type']=='application/pdf'
    assert pdf['body'].startswith(b'%PDF-')
    assert pdf['headers']['Cache-Control']=='no-store'
    assert pdf['headers']['Content-Disposition'].endswith('"CropNova-Farm-Assessment.pdf"')
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf['body'])).pages)
    assert 'This crop matches the recorded screening checks.' in text
    assert 'Sources used' in text
    assert 'Questions still to resolve' in text
    assert '650 mm' in text


def test_pdf_contains_personalised_location_and_unresolved_questions():
    token,report,result=saved_assessment(soil_ph='',district='Karnal')
    pdf=response(path='/reports/'+token+'.pdf')['body']
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert 'Karnal, Haryana' in text
    assert 'measured soil pH' in text
    assert 'Not provided' in text
    assert 'Questions still to resolve' in text
    assert 'FACT_' not in text
    assert 'CSP' not in text
    assert len(PdfReader(BytesIO(pdf)).pages)<=3


def test_preferred_ph_is_not_presented_as_crop_failure():
    _,report,result=saved_assessment(soil_ph=8)
    html=result['body'].decode()
    assert 'not a limit beyond which the crop cannot grow' in html
    assert not report['rejected_options']


def test_missing_input_is_not_described_as_missing_knowledge():
    _,report,_=saved_assessment(soil_ph='')
    ph=next(c for c in build_summary(report)['candidates'][0]['checks'] if c['name']=='Soil pH')
    assert ph['reference']=='Not compared until this detail is provided'


def test_invalid_input_is_422_and_retains_entries():
    result=response('POST','/assess',{**REFERENCE_PROFILES['reference-wheat'],'soil_ph':20})
    assert result['status']=='422 Unprocessable Entity'
    assert 'value="20"' in result['body'].decode()
    assert 'Please check these details' in result['body'].decode()


@pytest.mark.parametrize('path',['/reports/nope.pdf','/assessment/nope','/static/../../.env','/.env','/instance/assessments.sqlite3'])
def test_private_or_invalid_paths_are_not_downloadable(path):
    result=response(path=path)
    assert result['status']=='404 Not Found'


def test_report_expires_and_has_private_file_permissions(tmp_path,monkeypatch):
    import report_store
    token,report,_=saved_assessment()
    assert report_store.DATABASE_PATH.stat().st_mode & 0o777==0o600
    with patch('report_store.time.time',return_value=10**12):
        assert load_report(token) is None
        assert response(path='/reports/'+token+'.pdf')['status']=='404 Not Found'


@pytest.mark.parametrize('asset,content_type',[('/static/style.css','text/css'),('/static/app.js','text/javascript'),('/static/fields.svg','image/svg+xml')])
def test_public_assets_load(asset,content_type):
    result=response(path=asset)
    assert result['status']=='200 OK'
    assert result['headers']['Content-Type'].startswith(content_type)
    assert result['body']


def test_unsafe_input_is_escaped_in_page_and_pdf():
    token,_,result=saved_assessment(district='<script>alert(1)</script>')
    html=result['body'].decode()
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html
    pdf=response(path='/reports/'+token+'.pdf')
    assert pdf['status']=='200 OK'


def test_summary_does_not_change_recorded_decisions():
    report=assess(REFERENCE_PROFILES['reference-wheat']);original=deepcopy(report)
    summary=build_summary(report)
    assert summary['matches']==1
    assert report==original


def test_public_generated_wording_replaces_technical_labels_without_changing_values():
    from assessment_summary import explanation_text
    text='The CSP uses research dataset screening. Its constraints show a water shortfall of 300 mm.'
    result=explanation_text(text)
    assert 'CSP' not in result
    assert 'research dataset' not in result
    assert 'constraints' not in result
    assert 'water shortfall of 300 mm' in result


def test_pdf_preserves_generated_words_but_uses_plain_labels():
    report=assess(REFERENCE_PROFILES['reference-wheat'])
    report['generative_ai']={'status':'generated','explanations':[{'crop_id':'wheat','status':'feasible','text':'This assessment uses research dataset screening. Soil pH 7 matches the preferred range.','fact_ids':[]}]}
    pdf=create_pdf(report)
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert 'research dataset' not in text
    assert 'Soil pH 7 matches the preferred range.' in text


def test_personalised_report_is_visible_without_download_or_ai_request():
    with patch('app.generate_explanation',return_value={'status':'not_requested','explanations':[]}) as provider:
        token,_,result=saved_assessment()
        second=response(path='/assessment/'+token+'/report')
    html=second['body'].decode()
    assert 'id="field-report"' in html
    assert 'Your personalised report' in html
    assert 'Measured pH: 7' in html
    assert 'What still needs checking?' in html
    assert '/assessment/'+token in html
    assert 'Download my report' not in html
    assert 'Save a PDF copy' in html
    assert provider.call_count==1
