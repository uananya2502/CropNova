# Published crop requirements added

The knowledge base now has **41 facts and 17 source records** for four crops. This is enough to run four source-backed reference examples. It is not a field-validated recommendation system.

## Example inputs

Open an explicit example link such as `/?preset=reference-wheat`, `/?preset=reference-rice`, `/?preset=reference-chickpea` or `/?preset=reference-maize`. The ordinary home page starts blank. Each example selects one crop so region and water measurement remain clear.

| Crop | State | Season | Soil | pH | Water budget | Measurement basis | Drainage |
|---|---|---|---|---|---|---|---|
| Wheat | Haryana | Rabi | Loamy | 7 | 650 mm | Seasonal crop-water supply | Unknown is allowed |
| Rice | Haryana | Kharif | Clayey | 6 | 700 mm | Seasonal crop-water supply | Unknown is allowed |
| Chickpea | Haryana | Rabi | Loamy | 7 | 150 mm | Supplemental irrigation | Well drained |
| Maize | Rajasthan | Kharif | Loamy | 7 | 800 mm | Seasonal crop-water supply | Well drained |

Each example passes the four implemented screens and includes the facts and sources used. These inputs are examples, not measurements from real farms.

## What the sources support

- Wheat: preferred loam/clay loam and pH 6.5–7.5, from [MANAGE's DAESI study material](https://www.manage.gov.in/publications/eBooks/Revised%20DAESI%20Study%20Material.pdf), printed page 72.
- Rice: preferred clay/clay loam and good growth at pH 5.5–6.5, from [TNAU's rice guide](https://agritech.tnau.ac.in/expert_system/paddy/cultivationpractices1.html), “Soil Condition Required”. These are preferences; rice also grows in other soils.
- Chickpea: preferred deep loam/silty clay loam, good drainage, and ideal pH 6–8, from [NITI Aayog's 2025 pulses report](https://www.niti.gov.in/sites/default/files/2025-09/Strategies-and-Pathways-for-Accelerating-Growth-in-Pulses-towards-the-Goal-of-Atmanirbharta.pdf), section 3.5.5, printed pages 95–96.
- Maize: Rajasthan-specific soil, pH 6.5–7.5 and seasonal information, from the [Rajasthan maize value-chain report](https://environment.rajasthan.gov.in/content/dam/agriculture/Rajasthan%20Agricultural%20Competitiveness%20Project/valuechainreport/RACP_VC_Maize.pdf), sections 2.3 and 2.6. This evidence is not transferred to Haryana.
- Wheat, rice and maize: indicative seasonal crop evapotranspiration of 450–650, 450–700 and 500–800 mm respectively, from [FAO Table 14](https://www.fao.org/4/S2022E/s2022e07.htm).
- Chickpea: 100–150 mm supplemental irrigation alongside conserved soil moisture, from [NABARD/ICRIER's Water Productivity Mapping of Major Indian Crops](https://www.nitiforstates.gov.in/public-assets/Policy/policy-repo/water-and-wash/RNANAE000518.pdf), section 6.3.1, printed page 82. This is not chickpea's total seasonal water use.
- Haryana season records come from the [HSDC Rabi](https://haryanaseeds.org.in/products/field-crops/rabi-crops) and [Kharif](https://haryanaseeds.org.in/products/field-crops/kharif-crops) catalogues. The HHM-4 maize entry remains a variety reference.

## How the checks work

The numeric water input is a resource budget with a stated measurement basis. A budget below the reference range is marked a screening shortfall. A budget inside the range stays unresolved because local crop-water demand is unknown. A budget at or above the upper reference passes this limited reference comparison. It does not prescribe applying that much water or prove that irrigation infrastructure can supply it. Rainfall effectiveness, timing, losses, crop duration and local weather still matter; paddy preparation and seepage need separate estimates.

Published preferred pH ranges are not survival limits. Outside them, the system requests review rather than claiming that a crop cannot grow. Non-exhaustive soil and season lists work the same way. Drainage is checked when the source requires it. Unknown inputs and incompatible water bases cannot pass.

## Review and remaining work

New records have checked source extractions and identify the source section, scope and measurement basis. Independent team review and local agronomic validation remain outstanding, as required before using the prototype for real farming decisions. No accuracy percentage is claimed.

Next priorities are expert-reviewed cases covering matches, shortfalls and unknowns; local weather and effective-rainfall estimates; broader state-specific crop guidance; and documented evaluation against independent cases. Adding more crop names alone would not establish reliability.
