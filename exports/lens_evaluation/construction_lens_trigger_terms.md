# Construction Lens Trigger Vocabulary

- PDFs evaluated: 10
- Lens order: building_physics, materials, methods_tooling, failure, climate, compliance, insurance_risk

## building_physics
- thermal conductivity (physics_term): 116
- moisture (physics_term): 38
- comfort (physics_term): 11
- condensation (physics_term): 10
- insulation (assembly): 10
- heat flux (physics_term): 9
- u value (physics_term): 8
- mold (physics_term): 5
- wall (assembly): 5
- energy use (physics_term): 4
- indoor temperature (physics_term): 4
- relative humidity (physics_term): 4
- roof (assembly): 4
- glazing (assembly): 2
- infiltration (physics_term): 2
- air leakage (physics_term): 1
- facade (assembly): 1
- r value (physics_term): 1
- u-value (physics_term): 1
- ventilation rate (physics_term): 1

## materials
- steel (material): 45
- thermal conductivity (property): 39
- coating (material): 35
- concrete (material): 27
- modulus (property): 23
- compressive strength (property): 17
- porosity (property): 16
- elastic modulus (property): 14
- tensile strength (property): 14
- service life (property): 13
- durability (property): 11
- permeability (property): 11
- reinforced concrete (material): 9
- insulation (material): 8
- shear strength (property): 8
- masonry (material): 7
- yield strength (property): 7
- reinforcement (material): 6
- stainless steel (material): 5
- wood (material): 5

## methods_tooling
- results (test_marker): 233
- samples (test_marker): 158
- test (test_marker): 134
- measured (test_marker): 49
- tested (test_marker): 25
- specimen (test_marker): 21

## failure
- failure (high_signal): 218
- collapse (failure_mode): 212
- due to (causal_marker): 59
- forensic (high_signal): 35
- failed (high_signal): 24
- corrosion (failure_mode): 23
- fracture (failure_mode): 22
- seismic (failure_mode): 22
- fatigue (failure_mode): 16
- humidity (failure_mode): 16
- deterioration (failure_mode): 15
- cracking (failure_mode): 14
- condensation (failure_mode): 13
- caused by (causal_marker): 12
- degradation (failure_mode): 12
- buckling (failure_mode): 11
- attributed to (causal_marker): 6
- because of (causal_marker): 4
- settlement (failure_mode): 4
- mold (failure_mode): 2

## climate
- risk (resilience_term): 23
- moisture (hazard): 18
- wind (hazard): 18
- vulnerability (resilience_term): 13
- humidity (hazard): 7
- resilience (resilience_term): 3
- hazard (resilience_term): 2
- flood (hazard): 1
- high temperature (hazard): 1
- icing (hazard): 1

## compliance
- astm (std_token): 50
- asce (std_token): 29
- aci (std_token): 24
- eurocode (std_token): 11
- in accordance with (pass_phrase): 5
- building code (code_phrase): 4
- ul (std_token): 3
- iso (std_token): 2
- meets (pass_phrase): 2
- ashrae (std_token): 1
- code requirement (code_phrase): 1
- icc (std_token): 1

## insurance_risk
- collapse (loss_cause): 92
- failure (risk_term): 38
- roof (system): 22
- foundation (system): 11
- wind (loss_cause): 11
- floor (system): 10
- wall (system): 10
- corrosion (risk_term): 7
- fire (loss_cause): 7
- damage (insurance_term): 6
- loss (insurance_term): 5
- repair (mitigation_term): 3
- flood (loss_cause): 2
- settlement (loss_cause): 2
- claims (insurance_term): 1
- electrical (system): 1
- losses (insurance_term): 1
- moisture (risk_term): 1
- mold (loss_cause): 1
- water damage (loss_cause): 1

## failure buckets
### moisture
- humidity: 16
- condensation: 13
- mold: 2

### structural
- collapse: 212
- fracture: 22
- seismic: 22
- fatigue: 16
- cracking: 14
- buckling: 11
- settlement: 4

### material
- corrosion: 23
- deterioration: 15
- degradation: 12

