"""Published-reference input examples, separate from the synthetic test fixtures.

These are example field values, not measurements collected from real farms.
The public home page starts blank; examples are only used when requested by URL.
"""
REFERENCE_PROFILES = {}
for crop,state,season,texture,ph,budget,basis in [
    ('wheat','Haryana','rabi','loamy','7','650','seasonal_crop_water'),
    ('rice','Haryana','kharif','clayey','6','700','seasonal_crop_water'),
    ('chickpea','Haryana','rabi','loamy','7','150','supplemental_irrigation'),
    ('maize','Rajasthan','kharif','loamy','7','800','seasonal_crop_water'),
    ('barley','Punjab','rabi','loamy','7','650','seasonal_crop_water'),
    ('cotton','Punjab','kharif','clay_loam','7','1300','seasonal_crop_water'),
    ('groundnut','Punjab','kharif','sandy_loam','6','700','seasonal_crop_water'),
    ('sorghum','Maharashtra','kharif','loamy','7','650','seasonal_crop_water'),
    ('pearl_millet','Haryana','kharif','sandy_loam','6','650','seasonal_crop_water'),
    ('soybean','Punjab','kharif','loamy','7','700','seasonal_crop_water'),
]:
    REFERENCE_PROFILES['reference-'+crop] = {
        'state':state,'season':season,'soil_texture':texture,'soil_ph':ph,
        'water_budget_mm':budget,'water_basis':basis,'soil_drainage':'well_drained',
        'candidate_ids':[crop],'objective':'find_suitable_crop',
    }
