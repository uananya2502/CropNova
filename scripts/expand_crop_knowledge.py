"""Reproduce the November 2026, source-reviewed knowledge expansion.

Run from the project root. Records have stable IDs, so running twice is safe.
Only season, texture, pH and water facts participate in the four crop checks.
Background facts are explicitly excluded from suitability decisions.
"""
import json
from pathlib import Path

PATH = Path('knowledge_base/data/knowledge_facts.json')
knowledge = json.loads(PATH.read_text())


def source(identity, organization, title, url, section):
    record = dict(source_id=identity, organization=organization, title=title,
                  url=url, section=section, review_status='reviewed_for_inclusion',
                  reviewed_on='2026-11-15',
                  review_notes='Listed sections inspected for the recorded facts. This is source review, not independent field validation.')
    if not any(s['source_id'] == identity for s in knowledge['sources']):
        knowledge['sources'].append(record)


source('SRC_PAU_KHARIF_2026', 'Punjab Agricultural University',
       'Package of Practices for Crops of Punjab, Kharif 2026',
       'https://pau.edu/content/ccil/pf/pp_kharif.pdf',
       'Contents; maize p.28, bajra p.41, cotton p.45, soybean p.73, groundnut p.96. Punjab scope.')
source('SRC_PAU_RABI_2025', 'Punjab Agricultural University',
       'Package of Practices for Crops of Punjab, Rabi 2025–26',
       'https://pau.edu/content/ccil/pf/pp_rabi.pdf',
       'Contents; wheat p.1, barley pp.23–24, gram p.34. Punjab scope.')
source('SRC_TNAU_ACIDITY', 'Tamil Nadu Agricultural University',
       'Problem soils and their management — crop pH reference table',
       'https://agritech.tnau.ac.in/pdf/3.pdf',
       'Printed p.79 (PDF p.23): optimum pH table in acidity-management discussion. Preferred ranges, not exclusion limits.')
source('SRC_TNAU_SOYBEAN', 'Tamil Nadu Agricultural University',
       'Agritech: Soybean — soil, climate and cultivation',
       'https://agritech.tnau.ac.in/horticulture/horti_vegetables_soybean.html',
       'Soil, season, sowing and harvesting sections; India cultivation context.')
source('SRC_CBSE_GROUNDNUT', 'Central Board of Secondary Education',
       'Basic Agriculture, Class X — groundnut cultivation',
       'https://cbseacademic.nic.in/web_material/Curriculum/Vocational/2018/Basic%20Agriculture%20X%20%28408%29.pdf',
       'Groundnut: climate and soil, cropping systems, nutrient requirement. Educational reference; confirm local practices.')


source('SRC_ICAR_MAHARASHTRA_SORGHUM', 'Indian Council of Agricultural Research',
       'Maharashtra — sorghum growing seasons',
       'https://www.icar.org.in/index.php/hi/node/17272',
       'Sorghum section: grain and fodder cultivation in Kharif and Rabi in Maharashtra. Historical cultivation context; no current area statistics used.')


def fact(crop, prop, value, sources, statement, *, state=None, eligible=True, **extra):
    suffix = state.upper().replace(' ', '_') if state else 'INDIA'
    identity = f'FACT_{crop.upper()}_{prop.upper()}_{suffix}_20261115'
    record = dict(fact_id=identity, crop_id=crop, property=prop,
                  category='season' if prop == 'growing_season' else 'water' if 'water' in prop or 'drought' in prop else 'soil' if 'soil' in prop else 'crop_context',
                  value=value, statement=statement, source_ids=sources,
                  applicability={'country': 'India', **({'state': state} if state else {})},
                  verification_status='verified_context_specific' if state else 'verified_general',
                  confidence='medium', constraint_eligible=eligible,
                  notes='Published-reference screening. Local variety, weather and management still require confirmation.', **extra)
    knowledge['facts'] = [f for f in knowledge['facts'] if f['fact_id'] != identity]
    knowledge['facts'].append(record)


new_crops = [
    ('barley', 'Barley', 'Hordeum vulgare', 'cereal'),
    ('cotton', 'Cotton', 'Gossypium spp.', 'fibre'),
    ('groundnut', 'Groundnut', 'Arachis hypogaea', 'oilseed_legume'),
    ('sorghum', 'Sorghum', 'Sorghum bicolor', 'cereal'),
    ('pearl_millet', 'Pearl millet', 'Pennisetum glaucum', 'cereal'),
    ('soybean', 'Soybean', 'Glycine max', 'oilseed_legume'),
]
for identity, name, scientific, group in new_crops:
    if not any(c['crop_id'] == identity for c in knowledge['crops']):
        knowledge['crops'].append(dict(crop_id=identity, common_name=name,
            scientific_name=scientific, crop_group=group, fact_ids=[], source_ids=[], status='active_prototype'))

# Regional seasons stay regional. A season not listed is left open, not rejected.
for crop in ['wheat', 'chickpea', 'barley']:
    fact(crop, 'growing_season', ['rabi'], ['SRC_PAU_RABI_2025'],
         'Included in the Punjab Rabi package.', state='Punjab', closed_world=False)
for crop in ['rice', 'maize', 'cotton', 'groundnut', 'pearl_millet', 'soybean']:
    fact(crop, 'growing_season', ['kharif'], ['SRC_PAU_KHARIF_2026'],
         'Included in the Punjab Kharif package.', state='Punjab', closed_world=False)
for crop in ['barley']:
    fact(crop, 'growing_season', ['rabi'], ['SRC_HSDC_RABI'],
         'Haryana seed catalogue lists barley under Rabi crops.', state='Haryana', closed_world=False)
for crop in ['cotton', 'pearl_millet']:
    fact(crop, 'growing_season', ['kharif'], ['SRC_HSDC_KHARIF'],
         'Haryana catalogue includes cotton and bajra under Kharif.', state='Haryana', closed_world=False)
# National Rabi sorghum examples must not imply local suitability in every state.
knowledge['facts'] = [f for f in knowledge['facts']
                      if f['fact_id'] != 'FACT_SORGHUM_GROWING_SEASON_INDIA_20261115']
fact('sorghum', 'growing_season', ['kharif', 'rabi'], ['SRC_ICAR_MAHARASHTRA_SORGHUM'],
     'ICAR describes both sorghum seasons in Maharashtra.', state='Maharashtra', closed_world=False)
# Use the explicitly named national Kharif classification for soybean.
# Restrict it to listed major growing states, preserving the Punjab-specific record.
for state in ['Madhya Pradesh', 'Maharashtra', 'Rajasthan', 'Telangana', 'Karnataka']:
    fact('soybean', 'growing_season', ['kharif'], ['SRC_MANAGE_DAESI'],
         'Soybean is primarily Kharif; the chapter names this growing state.', state=state, closed_world=False)

# Soil and pH: non-exhaustive preferences never become absolute survival limits.
textures = ['sandy', 'sandy_loam', 'loamy', 'clay_loam', 'clayey', 'silt_loam', 'silty_clay_loam']
fact('barley', 'soil_texture', textures, ['SRC_PAU_RABI_2025'],
     'Punjab barley guidance allows well-drained soils without a texture exclusion.',
     state='Punjab', closed_world=False, requires_drainage='well_drained')
fact('cotton', 'soil_texture', [s for s in textures if s != 'sandy'], ['SRC_PAU_KHARIF_2026'],
     'Punjab cotton guidance excludes sandy, saline and waterlogged fields; drainage is necessary.',
     state='Punjab', closed_world=False, requires_drainage='well_drained',
     limitations=['Salinity is not measured by the current form.'])
for crop in ['sorghum', 'pearl_millet']:
    fact(crop, 'soil_texture', ['loamy', 'sandy_loam'], ['SRC_MANAGE_DAESI'],
         'Millet chapter prefers drained loam or sandy loam.', closed_world=False, requires_drainage='well_drained')
fact('groundnut', 'soil_texture', ['sandy_loam'], ['SRC_CBSE_GROUNDNUT'],
     'Groundnut prefers light, loose, drained sandy loam; the source also names sandy clay loam, which the form does not represent.',
     closed_world=False, requires_drainage='well_drained')
fact('soybean', 'soil_texture', ['loamy'], ['SRC_TNAU_SOYBEAN'],
     'Soybean prefers fertile, well-drained loam; waterlogging harms growth.', closed_world=False, requires_drainage='well_drained')
fact('maize', 'soil_texture', ['sandy_loam', 'silt_loam'], ['SRC_PAU_KHARIF_2026'],
     'Punjab maize prefers well-drained sandy loam to silty loam.', state='Punjab', closed_world=False, requires_drainage='well_drained')
for crop, ph, src in [
    ('barley', [6, 7.5], 'SRC_TNAU_ACIDITY'),
    ('sorghum', [6, 7.5], 'SRC_TNAU_ACIDITY'),
    ('pearl_millet', [5, 6.5], 'SRC_TNAU_ACIDITY'),
    ('cotton', [6.5, 8], 'SRC_MANAGE_DAESI'),
    ('groundnut', [5.5, 7], 'SRC_CBSE_GROUNDNUT'),
    ('soybean', [6, 7.5], 'SRC_TNAU_SOYBEAN'),
]:
    fact(crop, 'soil_ph_range', ph, [src],
         'Published preferred pH reference; values outside it need review rather than automatic rejection.',
         range_kind='preferred', **({'reference_group': 'millets', 'limitations':['The pH reference describes the millet group; local pearl millet variety guidance still needs confirmation.']} if crop == 'pearl_millet' else {}))
fact('maize', 'soil_ph_range', [6, 7.5], ['SRC_TNAU_ACIDITY'],
     'General cereal pH reference applied to the Punjab comparison; not a Punjab-specific field measurement.', state='Punjab', range_kind='preferred')

for crop, water in [('barley',[450,650]), ('cotton',[700,1300]),
                    ('groundnut',[500,700]), ('sorghum',[450,650]),
                    ('pearl_millet',[450,650]), ('soybean',[450,700])]:
    fact(crop, 'water_screening_range_mm', water, ['SRC_FAO_SEASONAL_WATER'],
         'FAO indicative whole-season water-use envelope; not an irrigation allocation.',
         unit='mm', water_basis='seasonal_crop_water', range_kind='indicative', requires_local_confirmation=True,
         **({'reference_group':'sorghum/millet'} if crop == 'pearl_millet' else {}))

# Background reference records enrich the library but never decide suitability.
for crop, days, drought in [
    ('wheat',[120,150],'low-medium'), ('barley',[120,150],'low-medium'),
    ('rice',[90,150],'high'), ('maize',[125,180],'medium-high'),
    ('cotton',[180,195],'low'), ('groundnut',[130,140],'low-medium'),
    ('sorghum',[120,130],'low'), ('pearl_millet',[105,140],'low'),
    ('soybean',[135,150],'low-medium'),
]:
    fact(crop, 'indicative_duration_days', days, ['SRC_FAO_SEASONAL_WATER'],
         'FAO approximate growing-period envelope; local cultivar duration takes precedence.', eligible=False, unit='days')
    fact(crop, 'relative_drought_sensitivity', drought, ['SRC_FAO_SEASONAL_WATER'],
         'Relative drought-sensitivity category in FAO Table 14; not a field outcome forecast.', eligible=False)

for crop, prop, value, statement, src, state in [
 ('barley','sowing_window','15 October–15 November','Punjab barley sowing window.','SRC_PAU_RABI_2025','Punjab'),
 ('barley','growth_climate','cool early growth; warm dry maturity','Barley climate pattern in Punjab guide.','SRC_PAU_RABI_2025','Punjab'),
 ('cotton','sowing_window','1 April–15 May','Punjab cotton sowing window.','SRC_PAU_KHARIF_2026','Punjab'),
 ('cotton','preferred_soil_depth_cm',[100,120],'Cotton preferred rooting-soil depth.','SRC_MANAGE_DAESI',None),
 ('cotton','vegetative_temperature_c',[25,30],'Cotton vegetative optimum.','SRC_MANAGE_DAESI',None),
 ('cotton','fruiting_temperature_c',[22,27],'Cotton flowering/fruiting optimum.','SRC_MANAGE_DAESI',None),
 ('cotton','frost_free_period_days',[180,200],'Cotton requires a long frost-free period.','SRC_MANAGE_DAESI',None),
 ('soybean','preferred_air_temperature_c',[26.5,30],'Soybean preferred air temperature depends on variety.','SRC_TNAU_SOYBEAN',None),
 ('soybean','minimum_germination_soil_temperature_c',15.5,'Warm soil favours soybean emergence.','SRC_TNAU_SOYBEAN',None),
 ('soybean','sowing_depth_cm',[3,4],'Soybean sowing-depth reference under suitable moisture.','SRC_TNAU_SOYBEAN',None),
 ('soybean','row_spacing_cm',[45,60],'Soybean row-spacing reference.','SRC_TNAU_SOYBEAN',None),
 ('soybean','plant_spacing_cm',[4,5],'Soybean plant-spacing reference.','SRC_TNAU_SOYBEAN',None),
 ('soybean','maturity_signs','yellowing leaves; dry pods','Leaf yellowing and drying pods indicate soybean maturity.','SRC_TNAU_SOYBEAN',None),
 ('groundnut','rotation_options',['wheat','barley','chickpea'],'Groundnut rotation examples, not an automatically generated rotation plan.','SRC_CBSE_GROUNDNUT',None),
 ('groundnut','soil_calcium_context','calcium supports pod and kernel development','Soil calcium matters for groundnut pod development; no dose is inferred.','SRC_CBSE_GROUNDNUT',None),
]:
    fact(crop, prop, value, [src], statement, state=state, eligible=False)

# Keep the crop-to-fact/source index in sync for retrieval and validation.
for crop in knowledge['crops']:
    records = [f for f in knowledge['facts'] if f['crop_id'] == crop['crop_id']]
    crop['fact_ids'] = [f['fact_id'] for f in records]
    crop['source_ids'] = list(dict.fromkeys(s for f in records for s in f['source_ids']))
knowledge['metadata'].update(version='0.4.0', last_expanded='2026-11-15',
    expansion_note='Ten crops; scoped regional seasons and soil/pH/water references. Background records do not create extra suitability checks.')
from knowledge_base.validator import validate_knowledge
errors = validate_knowledge(knowledge)
if errors:
    raise ValueError(errors)
PATH.write_text(json.dumps(knowledge, indent=2, ensure_ascii=False) + '\n')
print(f"{len(knowledge['crops'])} crops, {len(knowledge['facts'])} facts, {len(knowledge['sources'])} sources")
