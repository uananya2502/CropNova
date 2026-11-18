"""Integration checks for new evidence, leading matches and compact comparisons."""
from copy import deepcopy
import json
from unittest.mock import patch
import pytest
from agent import run_assessment
from assessment_summary import build_summary
from crop_results import crop_findings, ordered_candidates
from knowledge_base.loader import load_knowledge
from knowledge_base.validator import validate_knowledge
from knowledge_base.retrieval import get_usable_facts
from public_profiles import REFERENCE_PROFILES
from tests.test_multipage import request
from assessment_questions import answer_question

NEW_CROPS = ['barley', 'cotton', 'groundnut', 'sorghum', 'pearl_millet', 'soybean']


def test_expansion_has_referenced_facts_and_explicit_background_separation():
    knowledge = load_knowledge()
    assert not validate_knowledge(knowledge)
    assert len(knowledge['crops']) == 10
    assert len(knowledge['facts']) == 640
    assert len({f['fact_id'] for f in knowledge['facts']}) == 640
    new = [f for f in knowledge['facts'] if f['fact_id'].endswith('20261115')]
    assert len(new) == 71
    assert all(f in get_usable_facts(knowledge) for f in new)
    background = [f for f in new if f.get('constraint_eligible') is False]
    assert len(background) == 33
    assert all(f['property'] not in {'growing_season','soil_texture','soil_ph_range','water_screening_range_mm'} for f in background)


@pytest.mark.parametrize('crop', NEW_CROPS)
def test_new_crops_have_complete_reference_profiles_and_one_leading_card(crop):
    report = run_assessment(REFERENCE_PROFILES['reference-' + crop])
    summary = build_summary(report)
    assert summary['matches'] == 1
    assert summary['candidates'][0]['matched'] == 4
    html = crop_findings(summary['candidates'])
    assert f'data-leading-crop="{crop}"' in html
    assert 'Why this crop is shown first' in html
    assert all(check['sources'] for check in summary['candidates'][0]['checks'])


def test_state_specific_sorghum_season_does_not_transfer_to_punjab():
    report = run_assessment({**REFERENCE_PROFILES['reference-sorghum'], 'state':'Punjab'})
    candidate = build_summary(report)['candidates'][0]
    assert candidate['status'] == 'unknown'
    assert next(c for c in candidate['checks'] if c['name']=='Growing season')['status'] == 'unknown'
    assert 'data-leading-crop=' not in crop_findings([candidate])


def test_all_crops_punjab_clayey_field_promotes_supported_barley_before_others():
    report = run_assessment({**REFERENCE_PROFILES['reference-barley'],
                             'soil_texture':'clayey','candidate_ids':[]})
    candidates = build_summary(report)['candidates']
    assert candidates[0]['id'] == 'barley' and candidates[0]['status'] == 'feasible'
    html = crop_findings(candidates)
    assert html.index('data-leading-crop="barley"') < html.index('Other crop options')
    assert 'Compare the four checked conditions' in html
    assert sum(c['status'] == 'feasible' for c in candidates) == 1


def test_equal_matches_share_leading_status_and_no_unique_winner_is_invented():
    report = run_assessment({**REFERENCE_PROFILES['reference-barley'],
                             'candidate_ids':['wheat','barley']})
    candidates = build_summary(report)['candidates']
    assert [c['id'] for c in candidates] == ['barley','wheat']
    html = crop_findings(candidates)
    assert html.count('Joint leading match') == 2
    assert 'do not establish a single best crop' in html


def test_no_match_screen_preserves_unknowns_and_water_shortfall():
    report = run_assessment({**REFERENCE_PROFILES['reference-cotton'],
                             'water_budget_mm':'100', 'candidate_ids':[]})
    summary = build_summary(report)
    assert summary['matches'] == 0
    html = crop_findings(summary['candidates'])
    assert 'No complete match yet' in html and 'data-leading-crop=' not in html
    assert 'Shortfall / mismatch' in html


def test_ranking_is_display_only_and_never_changes_engine_outcomes():
    report = run_assessment({**REFERENCE_PROFILES['reference-wheat'], 'candidate_ids':[]})
    original = deepcopy(report)
    summary = build_summary(report)
    crop_findings(summary['candidates'])
    assert report == original
    groups = [c['status'] for c in summary['candidates']]
    assert groups == sorted(groups, key={'feasible':0,'unknown':1,'rejected':2}.get)


def test_published_library_shows_counts_and_qualified_background():
    html = request('/sources')['body'].decode()
    assert '640 records in total' in html
    assert 'Additional crop background' in html
    assert 'not additional suitability checks' in html
    assert 'Pearl millet' in html and 'Punjab' in html


@pytest.mark.parametrize('alias', ['bajra', 'pearl millet', 'peanut', 'soybean', 'jowar'])
def test_question_crop_filters_recognize_new_names_before_retrieval(alias):
    report = run_assessment(REFERENCE_PROFILES['reference-wheat'])
    with patch('assessment_questions.search_assessment') as search:
        answer = answer_question(report, f'Is the soil suitable for {alias}?')
    assert answer['status'] == 'no_evidence'
    assert 'not included' in answer['answer']
    search.assert_not_called()
