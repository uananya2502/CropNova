"""Follow-up answers must cite evidence and preserve recorded decisions."""
from copy import deepcopy
from io import BytesIO
import json
from unittest.mock import patch

import pytest

import assessment_questions as questions
import semantic_search as search
from app import assess, application
from public_profiles import REFERENCE_PROFILES
from report_store import save_report, load_report
from web_views import result_page


@pytest.fixture
def report():
    return assess(REFERENCE_PROFILES['reference-wheat'])


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr('report_store.DATABASE_PATH',tmp_path/'reports.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    monkeypatch.setenv('AI_PROVIDER','gemini')
    questions.CACHE.clear()
    questions.WINDOWS.clear()


def written(report, records):
    return {'kind':'answered','answer':'The entered water budget matches the published range. Confirm local water timing.',
            'assessment_status':report['status'],
            'crop_statuses':[{'crop_id':key,'status':value} for key,value in questions.crop_decisions(report).items()],
            'evidence_ids':[records[0]['id']]}


def request(token, data, raw=None):
    body=json.dumps(data).encode() if raw is None else raw
    output={}
    def start(status,headers): output.update(status=status,headers=dict(headers))
    output['body']=json.loads(b''.join(application({'REQUEST_METHOD':'POST','PATH_INFO':f'/assessment/{token}/ask','CONTENT_LENGTH':str(len(body)),'wsgi.input':BytesIO(body)},start)))
    return output


def test_documents_only_include_selected_crop_and_reviewed_sources(report):
    docs=search.assessment_documents(report)
    assert len(docs)==5
    assert all(row['crop_id']=='wheat' for row in docs)
    assert any('650' in row['text'] for row in docs)
    assert all(source['review_status']=='reviewed_for_inclusion' for row in docs for source in row['sources'])


def test_unreviewed_sources_are_removed_from_search(report):
    for source in report['evidence']:source['review_status']='pending'
    assert search.assessment_documents(report)==[]


def test_out_of_scope_references_are_removed(report):
    report['profile']['region']['state']='Kerala'
    docs=search.assessment_documents(report)
    # General water evidence can remain, but Haryana-specific season references cannot.
    assert not any(row['title']=='Wheat · Growing season' for row in docs)


def test_search_ranks_normalized_vectors_and_respects_threshold(report):
    import numpy as np
    records=search.assessment_documents(report)[:3]
    class Encoder:
        def encode(self,*args,**kwargs): return np.array([[1.,0.]])
    with patch.object(search,'assessment_documents',return_value=records), patch.object(search,'load_encoder',return_value=Encoder()), patch.object(search,'document_vectors',return_value=np.array([[0.,1.],[1.,0.],[-1.,0.]])):
        result=search.search_assessment(report,'water',top_k=2,minimum_similarity=.28)
    assert [row['id'] for row in result]==[records[1]['id']]


def test_answer_cites_retrieved_evidence_without_mutating_report(report):
    before=deepcopy(report)
    records=search.assessment_documents(report)
    with patch.object(questions,'search_assessment',return_value=records), patch.object(questions,'call_gemini',return_value=written(report,records)) as model:
        result=questions.answer_question(report,'Why does wheat match?')
    assert result['status']=='answered'
    assert len(result['evidence'])==1
    assert 'similarity' not in result['evidence'][0]
    assert report==before
    context=model.call_args.args[0]
    assert 'district' not in context and 'region' not in context


@pytest.mark.parametrize('change', ['assessment_status','crop_status','unknown_crop','duplicate_crop','citation','no_citation','extra_field'])
def test_changed_decisions_and_fabricated_citations_are_rejected(report,change):
    records=search.assessment_documents(report)
    answer=written(report,records)
    if change=='assessment_status':answer['assessment_status']='OTHER'
    if change=='crop_status':answer['crop_statuses'][0]['status']='rejected'
    if change=='unknown_crop':answer['crop_statuses'][0]={'crop_id':'potato','status':None}
    if change=='duplicate_crop':answer['crop_statuses']*=2
    if change=='citation':answer['evidence_ids']=['invented']
    if change=='no_citation':answer['evidence_ids']=[]
    if change=='extra_field':answer['recommendation']='plant potatoes'
    with pytest.raises(ValueError):questions.validate_written_answer(answer,report,records)


@pytest.mark.parametrize('question',['What pesticide should I spray?','What is the rice result?'])
def test_unsupported_topics_do_not_call_models(report,question):
    with patch.object(questions,'search_assessment') as encoder,patch.object(questions,'call_gemini') as model:
        assert questions.answer_question(report,question)['status']=='no_evidence'
    encoder.assert_not_called();model.assert_not_called()


def test_missing_transformer_is_honest(report):
    with patch.object(questions,'search_assessment',side_effect=search.SearchUnavailable()):
        assert questions.answer_question(report,'Is water enough?')['status']=='search_unavailable'


def test_no_key_still_shows_findings(report,monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY')
    with patch.object(questions,'search_assessment',return_value=search.assessment_documents(report)),patch.object(questions,'call_gemini') as model:
        result=questions.answer_question(report,'Is water enough?')
    assert result['status']=='evidence_only' and result['evidence']
    model.assert_not_called()


def test_provider_failure_keeps_retrieved_evidence(report):
    with patch.object(questions,'search_assessment',return_value=search.assessment_documents(report)),patch.object(questions,'call_gemini',side_effect=TimeoutError):
        assert questions.answer_question(report,'Is water enough?')['status']=='evidence_only'


def test_endpoint_private_report_cache_and_readonly(report):
    token=save_report(report)
    with patch.object(questions,'answer_question',return_value={'status':'answered','answer':'Saved finding.','evidence':[]}) as model:
        first=request(token,{'question':'Why wheat?'})
        second=request(token,{'question':'Why wheat?'})
    assert first==second and first['status']=='200 OK'
    assert model.call_count==1
    assert load_report(token)==report
    assert first['headers']['Cache-Control']=='no-store'


@pytest.mark.parametrize('data',[{},[],{'question':'x'},{'question':'x'*401},{'question':'Why wheat?','crop_id':'rice'}])
def test_endpoint_validates_inputs(report,data):
    assert request(save_report(report),data)['status']=='400 Bad Request'


def test_invalid_json_and_expired_link(report):
    assert request(save_report(report),None,raw=b'not json')['status']=='400 Bad Request'
    assert request('expired',{'question':'Why wheat?'})['status']=='404 Not Found'


def test_per_report_rate_limit(report):
    token=save_report(report)
    with patch.object(questions,'answer_question',return_value={'status':'no_evidence','answer':'Not covered.','evidence':[]}):
        for index in range(6):assert request(token,{'question':f'Question {index}'})['status']=='200 OK'
        assert request(token,{'question':'Another question'})['status']=='429 Too Many Requests'


def test_page_has_plain_language_question_box(report):
    html=result_page(report,'private-token').decode()
    assert 'Ask about your assessment' in html
    assert '/assessment/private-token/ask' in html
    assert 'Google Gemini' in html
    assert 'CSP' not in html and 'embeddings' not in html
