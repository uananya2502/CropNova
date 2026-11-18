"""Report evidence readiness independently of the user's suitability outcome."""
from copy import deepcopy
from constraint_definitions import DEFAULT_CONSTRAINTS, CheckStatus, verified_facts
from evidence import values, numeric_range


def knowledge_coverage(candidates, profile):
    rows = []
    for crop in candidates:
        probe = deepcopy(profile)
        probe.setdefault('soil', {}).update(texture='loamy', ph=7.0, drainage='well_drained')
        probe.setdefault('water', {}).update(availability='moderate')
        probe['season'] = profile.get('season') or 'rabi'
        facts = crop.get('facts', [])
        # Use documented example values only to ask whether each check has usable
        # evidence. Region stays unchanged; these values never enter assessment.
        for prop, path in [('growing_season', ('season',)), ('soil_texture', ('soil', 'texture'))]:
            matches = verified_facts(facts, {prop}, profile)
            if matches:
                choices = values(matches[0].get('value'))
                if choices:
                    if len(path) == 1:
                        probe[path[0]] = choices[0]
                    else:
                        probe[path[0]][path[1]] = choices[0]
        for prop in ('soil_ph_range', 'water_screening_range_mm'):
            matches = verified_facts(facts, {prop}, profile)
            if matches:
                try:
                    low, high = numeric_range(matches[0]['value'])
                    if prop == 'soil_ph_range':
                        probe['soil']['ph'] = (low + high) / 2
                    else:
                        probe['water'].update(budget_mm=high, basis=matches[0].get('water_basis'))
                except (ValueError, TypeError, KeyError):
                    pass
        outcomes = [check.check(crop, probe, facts) for check in DEFAULT_CONSTRAINTS]
        rows.append({'crop_id': crop['crop_id'], 'name': crop['name'],
                     'ready_checks': sum(c.status is not CheckStatus.UNKNOWN for c in outcomes),
                     'total_checks': len(outcomes),
                     'checks': [{'name': c.name, 'ready': c.status is not CheckStatus.UNKNOWN,
                                 'reason': c.reason, 'reason_code': c.reason_code} for c in outcomes]})
    return rows
