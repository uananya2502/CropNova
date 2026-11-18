"""Reproducible coverage audit, including each published-reference example."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import run_assessment
from demo import BASE, PRESETS

if __name__ == '__main__':
    report = run_assessment({**BASE, 'mode': 'real'})
    audit = {key: report.get(key) for key in ['status','knowledge_version','knowledge_summary','knowledge_coverage']}
    audit['reference_examples'] = {}
    for key, (_, profile) in PRESETS.items():
        if key.startswith('reference-'):
            result = run_assessment(profile)
            audit['reference_examples'][key] = {field: result.get(field) for field in ('profile','status','knowledge_coverage','assessment_basis')}
    print(json.dumps(audit, indent=2))
