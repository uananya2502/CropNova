"""Practical next steps use saved evidence rather than invented farming advice."""
from copy import deepcopy
import pytest
from app import assess
from public_profiles import REFERENCE_PROFILES
from farm_next_steps import next_step_cards, render_next_steps
from tests.test_dropdown_form import response, FieldParser


def barley(**changes):
    return assess({**REFERENCE_PROFILES['reference-barley'], **changes})


def test_crop_menu_names_do_not_imply_a_single_growing_state():
    parser=FieldParser(); parser.feed(response('/assess')['body'].decode())
    from assessment_form import CROPS
    assert ('wheat','Wheat') in CROPS
    assert all('—' not in label and '/' not in label for _,label in CROPS)
    from form_choices import state_choices
    assert ('Punjab','Punjab') in state_choices()
    assert barley(candidate_ids=['wheat'])['status']=='FEASIBLE_OPTIONS_FOUND'


def test_matched_crop_still_has_practical_sourced_actions_and_published_dates():
    report=barley()
    crops,actions=next_step_cards(report)
    assert len(actions)==4 and crops[0]['id']=='barley'
    html=render_next_steps(report)
    assert '15 October–15 November' in html and '120–150 days' in html
    assert '650 mm' in html and 'Your entry:' in html
    assert 'relative effort points' not in html
    assert all(action['sources'] for action in actions)


def test_water_shortfall_action_is_specific_and_does_not_invent_more_water():
    _,actions=next_step_cards(barley(water_budget_mm='100'))
    assert actions[1]['title']=='Review the water shortfall before choosing'
    assert actions[1]['references'][0]['entered']=='100 mm'
    assert 'Do not assume an extra water source' in actions[1]['instruction']


def test_incompatible_water_measurement_gets_a_different_action():
    _,actions=next_step_cards(barley(water_basis='supplemental_irrigation'))
    assert actions[1]['title']=='Use the same kind of water estimate'


def test_old_saved_reports_without_context_snapshot_still_explain_actual_checks():
    report=barley();report.pop('field_guidance')
    html=render_next_steps(report)
    assert '650 mm' in html and 'Check soil and field drainage' in html
    assert '15 October' not in html


def test_background_snapshot_respects_location_and_is_not_decision_evidence():
    report=barley(state='Haryana')
    assert not any(f.get('property')=='sowing_window' for f in report['field_guidance']['facts'])
    assert not any(f.get('historical_reference') for f in report['field_guidance']['facts'])
    assert not any(f.get('property')=='sowing_window' for f in report['evidence_package']['facts'])


def test_unreviewed_or_wrong_scope_context_is_not_shown_as_a_sowing_instruction():
    report=barley()
    for source in report['field_guidance']['sources']:source['review_status']='needs_review'
    assert '15 October' not in render_next_steps(report)


def test_plan_view_does_not_change_any_saved_decision():
    report=barley();before=deepcopy(report)
    render_next_steps(report)
    assert report==before


def test_other_weak_crop_options_do_not_take_over_the_plan():
    crops,actions=next_step_cards(barley(candidate_ids=[]))
    assert {crop['id'] for crop in crops}=={'barley','wheat'}
    assert all({r['crop'] for r in action['references']}=={'Barley','Wheat'} for action in actions)


def test_no_measurement_does_not_become_an_irrigation_schedule():
    _,actions=next_step_cards(barley(water_budget_mm=''))
    assert actions[1]['title']=='Get a usable water estimate'
    assert 'not an instruction to apply' in actions[1]['instruction']
