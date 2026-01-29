# Standards & Compliance Lens v1
# Extracts code/standard references and compliance statements from construction science text.

LENS_ID = "standards_compliance_v1"

TARGET_ENTITIES = [
    "code_standard",
    "compliance_statement"
]

KEYWORDS = [
    # Standards
    "ASTM", "ACI", "ASCE", "IBC", "IECC", "ASHRAE", "Eurocode",
    # Compliance
    "compliance", "non-compliance", "meets requirements", "pass", "fail"
]

OUTPUT_TYPES = [
    "code_standard",
    "compliance_statement"
]
