"""Free-provider integration checks; no real network calls or keys."""
from io import BytesIO
import json
from unittest.mock import patch
from urllib.error import HTTPError
import pytest
from genai_explainer import generate_explanation, prepare_context
from gemini_provider import call_gemini
from tests.test_genai import assessment, valid_answer
from tests.test_app import request
from demo import PRESETS


def test_gemini_uses_existing_evidence_validation():
    report=assessment(); context=prepare_context(report)
    with patch.dict('os.environ',{'AI_PROVIDER':'gemini','GEMINI_API_KEY':'fake-google-key'},clear=True),patch('genai_explainer.call_gemini',return_value=valid_answer(context)) as call,patch('genai_explainer.call_openai') as paid:
        result=generate_explanation(report,requested=True)
    assert result['status']=='generated'
    assert result['provider']=='gemini'
    assert result['model']=='gemini-3.5-flash-lite'
    call.assert_called_once()
    paid.assert_not_called()


def test_missing_google_key_never_falls_back_to_paid_openai():
    with patch.dict('os.environ',{'AI_PROVIDER':'gemini','OPENAI_API_KEY':'fake-openai-key'},clear=True),patch('genai_explainer.call_openai') as paid:
        result=generate_explanation(assessment(),requested=True)
    assert result['status']=='not_configured'
    paid.assert_not_called()


def test_gemini_quota_does_not_trigger_paid_fallback():
    error=HTTPError('https://generativelanguage.googleapis.com',429,'limit',{},BytesIO(b'{}'))
    with patch.dict('os.environ',{'AI_PROVIDER':'gemini','GEMINI_API_KEY':'fake-google-key'},clear=True),patch('genai_explainer.call_gemini',side_effect=error),patch('genai_explainer.call_openai') as paid:
        result=generate_explanation(assessment(),requested=True)
    assert result['status']=='unavailable'
    assert 'free-tier quota' in result['message']
    paid.assert_not_called()


def test_gemini_cannot_change_recorded_decisions():
    context=prepare_context(assessment()); answer=valid_answer(context)
    answer['explanations'][0]['status']='rejected'
    with patch.dict('os.environ',{'AI_PROVIDER':'gemini','GEMINI_API_KEY':'fake-google-key'},clear=True),patch('genai_explainer.call_gemini',return_value=answer):
        result=generate_explanation(assessment(),requested=True)
    assert result['status']=='unavailable'
    assert not result['explanations']


def test_gemini_transport_uses_header_key_and_only_model_output():
    context=prepare_context(assessment()); answer=valid_answer(context)
    response={'candidates':[{'finishReason':'STOP','content':{'parts':[
        {'thought':True,'text':'Never return internal thoughts'},
        {'text':json.dumps(answer)},
    ]}}]}
    with patch('gemini_provider.urlopen',return_value=BytesIO(json.dumps(response).encode())) as opened:
        actual=call_gemini(context,'fake-google-key','gemini-3.5-flash-lite','Explain provided evidence',{})
    assert actual==answer
    args,kwargs=opened.call_args; payload=json.loads(args[0].data)
    assert 'fake-google-key' not in args[0].full_url
    assert args[0].get_header('X-goog-api-key')=='fake-google-key'
    assert payload['generationConfig']['maxOutputTokens']==3500
    assert payload['generationConfig']['responseMimeType']=='application/json'
    assert kwargs['timeout']==30


@pytest.mark.parametrize('status',['MAX_TOKENS','SAFETY','RECITATION','OTHER'])
def test_unfinished_google_results_are_not_shown(status):
    response={'candidates':[{'finishReason':status,'content':{'parts':[]}}]}
    with patch('gemini_provider.urlopen',return_value=BytesIO(json.dumps(response).encode())):
        with pytest.raises(ValueError):
            call_gemini({},'fake-key','gemini-3.5-flash-lite','Explain',{})


def test_website_names_selected_provider_and_exports_validated_text():
    with patch.dict('os.environ',{'AI_PROVIDER':'gemini','GEMINI_API_KEY':'fake-google-key'},clear=True),patch('genai_explainer.call_gemini',side_effect=lambda context,*args:valid_answer(context)):
        _,html=request('POST','/assess',{**PRESETS['reference-wheat'][1],'use_genai':'yes'})
    assert 'sent to Google Gemini' in html
    assert 'This crop matches the recorded screening checks.' in html
    assert 'fake-google-key' not in html


def test_unknown_provider_does_not_make_network_request():
    with patch.dict('os.environ',{'AI_PROVIDER':'not-a-provider'},clear=True),patch('genai_explainer.call_openai') as paid:
        assert generate_explanation(assessment(),requested=True)['status']=='not_configured'
    paid.assert_not_called()
