# PDR rule-authority matrix

Authority classes: EXPLICIT_GUIDE (the PDR guide's own text), AUTHOR_CLARIFICATION (the author's later statement), OWNER_APPROVED (owner decision / approved interpretation), CODE_CONVENTION (a convention the engine uses that nobody approved), NEW_RESEARCH_PROPOSAL (Phase 6.5 variants), UNRESOLVED.

| requirement | authority | implemented in baseline | variants |
|---|---|---|---|
| previous-day resistance zone = small box from candle body to upper wick | EXPLICIT_GUIDE (PDR guide, zone definition); body-based construction: OWNER_APPROVED (Phase 3.6) | yes | unchanged in all |
| market opens gap up; the session open is strictly above the zone ceiling | EXPLICIT_GUIDE ('Market must open gap up'); strictly-above: AUTHOR_APPROVED (PDR-B03) | yes | unchanged in all |
| price returns to the zone (retest) before entry | EXPLICIT_GUIDE ('Price returned to the zone ... Green candle formed after the interaction') | yes: first candle whose range meets the zone | unchanged in all |
| 'wait for a green candle' after the zone is tested | EXPLICIT_GUIDE (s.4.3) | green body OR lower-price rejection (CODE_CONVENTION for the rejection route) | B1/B2/C: green only; D: baseline test |
| no fixed body percentage or wick size is required | AUTHOR_CLARIFICATION (PDR-B04a) | yes (minimal confirmation, no numeric strength) | strength gates S60/S70/SD are separate research configurations |
| enter on the FIRST eligible confirmation candle, not the first candle of the session | OWNER_APPROVED clarification (Phase 5.2/5.3) | yes (first qualifying candle after the retest) | B1/B2/C test earlier-entry readings; D tests a later one |
| confirmation candle closes STRICTLY ABOVE the zone ceiling | AUTHOR_APPROVED / OWNER_INTERPRETATION (PDR-A01..A05; rule PDR-B05a is coded as an owner interpretation of the author's word, Phase 3.6 brief) | yes - part of the approved baseline | B1/B2 BYPASS it (AUTHOR_CONFIRMATION_REQUIRED); C and D keep it |
| the retest candle may NOT itself be the confirmation candle | CODE_CONVENTION / PROPOSED (PDR-A07); unresolved sequencing; the guide only says 'after the interaction' | yes (labelled provisional) | B2/C allow it (AUTHOR_CONFIRMATION_REQUIRED) |
| lower-price rejection / hammer is a valid confirmation | AUTHOR_CLARIFICATION (PDR-B04) with a provisional geometric definition | yes | B1/B2/C do not use it (green only); D uses it |
| second confirmation candle before entry | UNRESOLVED / NEW_RESEARCH_PROPOSAL (the author's suggestion; conditions undefined) | no | D: mechanical convention (any later independently eligible candle) |
| zone ceiling proximity tolerance; one signal per setup cycle; 13:00 cutoff | CODE_CONVENTION / shared controller rule | yes | unchanged in all |


A written guide that is less detailed than an approved interpretation does not make the approved rule an implementation defect; it makes the interpretation a candidate for author confirmation. The close-above-ceiling requirement therefore stays in the baseline.