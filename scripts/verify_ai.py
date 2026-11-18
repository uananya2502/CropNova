"""Check three website assessment cases and optionally make real AI requests.

Examples:
    python3 scripts/verify_ai.py          # local checks, no paid requests
    python3 scripts/verify_ai.py --live   # three real requests when configured
"""
import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlencode
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import application
from demo import PRESETS
from local_settings import load_local_settings


def run_checks(live=False):
    load_local_settings()
    provider = os.environ.get('AI_PROVIDER', 'openai').strip().lower()
    key_setting = 'GEMINI_API_KEY' if provider == 'gemini' else 'OPENAI_API_KEY'
    has_key = bool(os.environ.get(key_setting, '').strip())
    baseline = PRESETS['reference-wheat'][1]
    cases = [
        ('Supported match', baseline, 'FEASIBLE_OPTIONS_FOUND'),
        ('Water shortfall', {**baseline, 'water_budget_mm': '300'}, 'NO_FEASIBLE_OPTION'),
        ('Missing soil pH', {**baseline, 'soil_ph': ''}, 'MORE_INFORMATION_NEEDED'),
    ]
    results = []
    for name, profile, expected in cases:
        # Exercise the same POST handler and JSON export used by the website.
        values = {**profile, 'use_genai': 'yes' if live and has_key else 'no'}
        body = urlencode(values, doseq=True).encode('utf-8')
        response_status = []
        environ = {'REQUEST_METHOD': 'POST', 'PATH_INFO': '/report',
                   'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body)}
        def start_response(status, headers):
            response_status.append(status)
        report = json.loads(b''.join(application(environ, start_response)))
        result = {
            'case': name, 'inputs': profile, 'expected_status': expected,
            'actual_status': report['status'],
            'assessment_passed': report['status'] == expected and response_status == ['200 OK'],
            'ai_status': report['generative_ai']['status'],
            'ai_message': report['generative_ai']['message'],
            'ai_explanations': report['generative_ai']['explanations'],
        }
        results.append(result)
        print(f"{name}: {result['actual_status']} | AI: {result['ai_status']}")
    if not live:
        live_status = 'not_requested'
    elif not has_key:
        live_status = 'blocked_missing_api_key'
    elif all(case['ai_status'] == 'generated' for case in results):
        live_status = 'completed'
    else:
        live_status = 'failed_or_unavailable'
    summary = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'all_assessments_passed': all(case['assessment_passed'] for case in results),
        'live_ai_status': live_status,
        'provider': provider,
        'cases': results,
    }
    destination = Path(__file__).resolve().parents[1] / 'docs' / 'ai_verification.json'
    destination.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    print('Live AI:', live_status)
    print('Saved results to docs/ai_verification.json')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Make three real API requests; provider charges may apply.')
    options = parser.parse_args()
    summary = run_checks(live=options.live)
    successful = summary['all_assessments_passed'] and (not options.live or summary['live_ai_status'] == 'completed')
    sys.exit(0 if successful else 1)
