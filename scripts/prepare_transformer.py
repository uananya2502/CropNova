"""Download the pinned public model once, then verify a real semantic search."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic_search import load_encoder, search_assessment, MODEL_ID, MODEL_REVISION
from app import assess
from public_profiles import REFERENCE_PROFILES

if __name__ == '__main__':
    print('Preparing',MODEL_ID,flush=True)
    load_encoder(allow_download=True)
    report=assess(REFERENCE_PROFILES['reference-wheat'])
    records=search_assessment(report,'Is my water supply enough for wheat?')
    print('Pinned revision:',MODEL_REVISION)
    print('Retrieved evidence:',[record['title'] for record in records])
    if not records:raise SystemExit('No evidence retrieved; preparation check failed.')
    print('Local transformer is ready.')
