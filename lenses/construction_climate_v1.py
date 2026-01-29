# Climate Exposure & Resilience Lens v1
# Extracts hazards, exposure conditions, and resilience claims from construction science text.

LENS_ID = "climate_resilience_v1"

TARGET_ENTITIES = [
    "hazard",
    "exposure_condition",
    "impact",
    "measurement"
]

KEYWORDS = [
    # Hazards
    "flood", "heat wave", "wildfire smoke", "wind", "storm surge", "sea-level rise", "freeze-thaw",
    # Resilience
    "mitigation", "adaptation", "resilience"
]

OUTPUT_TYPES = [
    "hazard",
    "exposure_condition",
    "impact",
    "measurement"
]
