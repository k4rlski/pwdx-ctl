"""
addendum_ctl.router — Core addendum detection and field resolution logic.

Usage:
    from pwdx_ctl.addendum import needs_addendum, resolve_field, route_all_fields

    if needs_addendum(extracted['job_duties']):
        adtext = resolve_field(extracted['job_duties'], extracted.get('addendum_job_duties'))
"""

ADDENDUM_TRIGGERS = [
    "please see addendum",
    "please see attached",
    "see addendum",
    "see attached",
    "refer to addendum",
    "per addendum",
    "refer to attachment",
    "see attachment",
]

# Maps ETA-9141 extracted field → (addendum_field, crm_field, description)
FIELD_ROUTING_MAP = {
    "job_duties": {
        "addendum_field": "addendum_job_duties",
        "crm_field":      "adtextnews",
        "label":          "job duties / newspaper ad text",
        "fallback":       None,   # None = return trigger phrase if no addendum content
    },
    "education_major": {
        "addendum_field": "addendum_educ",
        "crm_field":      "jobeducation",
        "label":          "education requirements",
        "fallback":       None,
    },
    "soc_code": {
        "addendum_field": "addendum_soc",
        "crm_field":      "occupationtitlecode",
        "label":          "SOC code / occupation title",
        "fallback":       None,
    },
    "experience_months": {
        "addendum_field": "addendum_exp",
        "crm_field":      "jobexperience",
        "label":          "experience requirements",
        "fallback":       None,
    },
    "special_requirements": {
        "addendum_field": "addendum_special",
        "crm_field":      "specialrequirements",
        "label":          "special requirements / other skills",
        "fallback":       None,
    },
    "other_skills": {
        "addendum_field": "addendum_other",
        "crm_field":      "otherskills",
        "label":          "other skills",
        "fallback":       None,
    },
}


def needs_addendum(value: str) -> bool:
    """Return True if the field value is an addendum trigger phrase."""
    if not value:
        return False
    v = value.lower().strip()
    return any(trigger in v for trigger in ADDENDUM_TRIGGERS)


def resolve_field(primary_value: str, addendum_value: str | None, fallback: str = "") -> str:
    """
    Resolve the final value for a CRM field.

    If primary_value is a trigger phrase and addendum_value has real content → return addendum_value.
    Otherwise return primary_value (or fallback if both are empty).
    """
    if needs_addendum(primary_value):
        if addendum_value and len(addendum_value.strip()) > 10:
            return addendum_value.strip()
        return fallback or primary_value  # preserve trigger if no addendum content
    return primary_value or fallback


def route_all_fields(extracted: dict) -> dict:
    """
    Apply addendum routing to all mapped fields in an extracted PWD dict.

    Returns a new dict with CRM field names as keys and resolved values.
    Unmapped fields are passed through unchanged.

    Example:
        crm_fields = route_all_fields(extracted_fields)
        # crm_fields['adtextnews'] will have the real job duties, not "Please See Addendum"
    """
    result = {}
    routed_crm_fields = set()

    for extracted_field, routing in FIELD_ROUTING_MAP.items():
        primary_val  = extracted.get(extracted_field, "")
        addendum_val = extracted.get(routing["addendum_field"], "")
        crm_field    = routing["crm_field"]
        resolved     = resolve_field(primary_val, addendum_val, routing.get("fallback") or "")
        result[crm_field] = resolved
        routed_crm_fields.add(crm_field)

    # Pass through all other extracted fields that don't map to a CRM field
    for k, v in extracted.items():
        if k not in FIELD_ROUTING_MAP and k not in result:
            result[k] = v

    return result


def summarize_addenda(extracted: dict) -> list[dict]:
    """
    Return a list of addendum detections for logging/debugging.
    Each entry: {field, trigger, addendum_field, content_length, crm_field}
    """
    found = []
    for extracted_field, routing in FIELD_ROUTING_MAP.items():
        pv = extracted.get(extracted_field, "")
        av = extracted.get(routing["addendum_field"], "")
        if needs_addendum(pv):
            found.append({
                "field":          extracted_field,
                "trigger":        pv[:80],
                "addendum_field": routing["addendum_field"],
                "content_length": len(av),
                "crm_field":      routing["crm_field"],
                "resolved":       bool(av and len(av) > 10),
            })
    return found
