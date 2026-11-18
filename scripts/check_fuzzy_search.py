"""Repeatable checks of the implemented fuzzy index and A*/uniform-cost planner.

These are software examples, not field data or an agricultural accuracy study.
No external AI API is called and no PDF report is created.
"""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from agent import run_assessment
from preparation_planner import plan_assessment
from public_profiles import REFERENCE_PROFILES

VARIANTS = {
    'reference': {},
    'water_shortfall': {'water_budget_mm':'300'},
    'water_partial': {'water_budget_mm':'600'},
    'missing_ph': {'soil_ph':''},
    'missing_measurements': {'soil_ph':'','soil_texture':'unknown','water_budget_mm':'','season':'unknown'},
    'unsupported_location': {'state':'Unsupported State'},
    'other_water_basis': {'water_basis':'supplemental_irrigation'},
    'outside_preferred_ph': {'soil_ph':'8.2'},
}


def main():
    rows=[]
    for preset,profile in REFERENCE_PROFILES.items():
        for label,change in VARIANTS.items():
            report=run_assessment({**profile,**change})
            astar=report['preparation_plan']
            uniform=plan_assessment(report,algorithm='uniform_cost')
            assert astar['status']==uniform['status']
            assert astar['cost']==uniform['cost']
            row=report['fuzzy_analysis']['candidates'][0]
            rows.append({'preset':preset,'variant':label,'assessment_status':report['status'],
                         'fuzzy_status':row['status'],'alignment_index':row['score'],
                         'planning_status':astar['status'],'effort_points':astar['cost'],
                         'astar_expanded':astar['expanded'],'uniform_cost_expanded':uniform['expanded'],
                         'same_optimal_cost':True})
    result={'scope':f'{len(rows)} controlled software scenarios. Not agricultural accuracy or a representative benchmark.',
            'heuristic':'max of cheapest action costs covering each unmet requirement',
            'rows':rows,'all_costs_match_uniform_cost':True}
    output=Path(__file__).resolve().parents[1]/'docs/fuzzy_search_checks.json'
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(f'{len(rows)} A* / uniform-cost comparisons passed.')
    print('Missing-measurement wheat example:',next(row for row in rows if row['preset']=='reference-wheat' and row['variant']=='missing_measurements'))
    print(output)


if __name__=='__main__':main()
