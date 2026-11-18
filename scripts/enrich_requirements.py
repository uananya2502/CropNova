"""Add narrowly sourced requirements for preliminary reference screening.

No synthetic values or unsourced water-category conversions are introduced.
"""
import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'knowledge_base/data/knowledge_facts.json'
k=json.loads(P.read_text())
SOURCES=[
 ('SRC_MANAGE_DAESI','MANAGE DAESI revised study material','https://www.manage.gov.in/publications/eBooks/Revised%20DAESI%20Study%20Material.pdf','Wheat soil requirements, printed p.72, PDF p.85','National Institute of Agricultural Extension Management'),
 ('SRC_TNAU_RICE_SOIL','TNAU rice main field preparation','https://agritech.tnau.ac.in/expert_system/paddy/cultivationpractices1.html','Soil Condition Required','Tamil Nadu Agricultural University'),
 ('SRC_NITI_PULSES_2025','Strategies and Pathways for Accelerating Growth in Pulses','https://www.niti.gov.in/sites/default/files/2025-09/Strategies-and-Pathways-for-Accelerating-Growth-in-Pulses-towards-the-Goal-of-Atmanirbharta.pdf','Section 3.5.5 Chickpea, printed pp.95-96','NITI Aayog'),
 ('SRC_RACP_MAIZE','Rajasthan Agricultural Competitiveness Project Maize Value Chain Analysis','https://environment.rajasthan.gov.in/content/dam/agriculture/Rajasthan%20Agricultural%20Competitiveness%20Project/valuechainreport/RACP_VC_Maize.pdf','Sections 2.3 and 2.6, printed pp.16 and 20-21','Government of Rajasthan / Agri Business Promotion Facility'),
 ('SRC_ICRIER_CHICKPEA_WATER','Water Productivity Mapping of Major Indian Crops','https://www.nitiforstates.gov.in/public-assets/Policy/policy-repo/water-and-wash/RNANAE000518.pdf','Section 6.3.1, printed p.82, PDF p.110','NABARD and ICRIER, 2018'),
]
for sid,title,url,section,publisher in SOURCES:
 if not any(s.get('source_id')==sid for s in k['sources']):
  k['sources'].append(dict(source_id=sid,title=title,url=url,section=section,publisher=publisher,
    accessed_date='2026-10-29',review_status='reviewed_for_inclusion',
    review_notes='Source extraction checked for preliminary screening. Independent team agronomic review remains outstanding.'))
def add(crop,prop,value,src,statement,scope=None,**extra):
 fid=f'FACT_{crop.upper()}_{prop.upper()}_REF_V3'
 if any(f.get('fact_id')==fid for f in k['facts']):return
 category='water' if prop.startswith('water_') else 'season' if prop=='growing_season' else 'soil'
 scope=scope or {'country':'India'}
 k['facts'].append(dict(fact_id=fid,crop_id=crop,property=prop,category=category,value=value,
  statement=statement,source_ids=[src],applicability=scope,
  verification_status='verified_context_specific' if scope.get('state') else 'verified_general',
  confidence='medium',notes='Reference screening only. Preferred conditions are not absolute survival limits. Source extraction is not independent agronomic validation.',**extra))
 c=next(c for c in k['crops'] if c['crop_id']==crop)
 c['fact_ids'].append(fid)
 if src not in c['source_ids']:c['source_ids'].append(src)
add('wheat','soil_texture',['loamy','clay_loam'],'SRC_MANAGE_DAESI','Loam and clay loam with good structure are preferred wheat soils.',closed_world=False)
add('wheat','soil_ph_range',[6.5,7.5],'SRC_MANAGE_DAESI','The wheat chapter gives pH 6.5-7.5 as a preferred soil reaction.',range_kind='preferred')
add('rice','soil_texture',['clayey','clay_loam'],'SRC_TNAU_RICE_SOIL','Clay and clay loam retaining water are preferred for paddy; other soils may support rice.',closed_world=False)
add('rice','soil_ph_range',[5.5,6.5],'SRC_TNAU_RICE_SOIL','The rice guide describes good growth at pH 5.5-6.5; this is not a universal exclusion range.',range_kind='preferred')
add('chickpea','soil_texture',['loamy','silty_clay_loam'],'SRC_NITI_PULSES_2025','Deep loams and silty clay loams with good drainage are preferred.',closed_world=False,requires_drainage='well_drained')
add('chickpea','soil_ph_range',[6,8],'SRC_NITI_PULSES_2025','The India pulses report describes ideal pH 6.0-8.0.',range_kind='preferred')
add('maize','soil_texture',['loamy','silt_loam','silty_clay_loam'],'SRC_RACP_MAIZE','The Rajasthan guide prefers loam or silt loam surface soil and permeable subsoil.',{'country':'India','state':'Rajasthan'},closed_world=False,requires_drainage='well_drained')
add('maize','soil_ph_range',[6.5,7.5],'SRC_RACP_MAIZE','The Rajasthan maize guide gives pH 6.5-7.5 as preferred.',{'country':'India','state':'Rajasthan'},range_kind='preferred')
add('maize','growing_season',['kharif','rabi'],'SRC_RACP_MAIZE','The Rajasthan seasonal pattern describes Kharif and Rabi maize.',{'country':'India','state':'Rajasthan'},closed_world=False)
for crop,limits in [('wheat',[450,650]),('rice',[450,700]),('maize',[500,800])]:
 add(crop,'water_screening_range_mm',limits,'SRC_FAO_SEASONAL_WATER','Indicative whole-season crop evapotranspiration range, not irrigation volume. Compared only with a matching user-supplied seasonal crop-water budget.',unit='mm',water_basis='seasonal_crop_water',range_kind='indicative',requires_local_confirmation=True)
add('chickpea','water_screening_range_mm',[100,150],'SRC_ICRIER_CHICKPEA_WATER','The India report gives total supplemental irrigation of 100-150 mm for chickpea relying on conserved moisture. This is NOT total seasonal crop-water use.',unit='mm',water_basis='supplemental_irrigation',range_kind='indicative',requires_local_confirmation=True)
k['metadata'].update(version='0.3.0',status='preliminary_reference_screening',
 notice='Preliminary published-reference screening. Soil and pH preferences are not hard survival limits. Water uses its declared measurement basis. Independent local agronomic validation remains outstanding.',
 supported_region='Haryana season records for wheat, rice and chickpea; Rajasthan season/soil/pH records for maize. National references retain their own scope.')
P.write_text(json.dumps(k,indent=2,ensure_ascii=False)+'\n')
print('Facts:',len(k['facts']),'Sources:',len(k['sources']))
