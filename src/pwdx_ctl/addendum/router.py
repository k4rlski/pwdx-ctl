"""
addendum_ctl.router — Addendum trigger detection and field routing for ETA-9141 PWD extraction.

VERIFIED against t_e_s_t_p_e_r_m schema and 3,135 real PDFs (2026-03-12).

Reality (from corpus analysis):
  - Only ONE trigger phrase appears in practice: "Please See Addendum"
  - Only 3 addendum_* fields are produced by the extractor
  - Only 3 primary fields ever contain trigger phrases (+ 1 alias)
  - education_major is the dominant case (74%), job_duties is minority (12%)

CRM FIELD STATUS (confirmed from SHOW COLUMNS):
  jobeducation  ✅ exists — mediumtext
  jobtitle      ✅ exists — but SOC code/title has no dedicated CRM field
  adtextnews    ✅ exists — mediumtext (newspaper ad copy)
  jobexperience ✅ exists — mediumtext
  NOTE: No occupationtitlecode field exists. SOC destination = TBD, log only for now.
"""

# ── Trigger phrases ─────────────────────────────────────────────────────────
# Only "please see addendum" appears in practice (2,890 of 2,890 triggers).
# Others listed for completeness / future-proofing.
ADDENDUM_TRIGGERS = [
    "please see addendum",   # 100% of actual occurrences
    "see addendum",
    "please see attached",
    "see attached",
    "refer to addendum",
    "per addendum",
]

# ── Confirmed field routing map ──────────────────────────────────────────────
# Source: corpus analysis of 3,135 ETA-9141 PDFs + SHOW COLUMNS on t_e_s_t_p_e_r_m
#
# Format: extracted_field → {
#   addendum_field:  key in extractor output that holds the real content
#   crm_field:       actual column in t_e_s_t_p_e_r_m (None = no confirmed field)
#   frequency:       how often this trigger appears in PDFs (pct of addendum cases)
#   label:           human description
# }

FIELD_ROUTING_MAP = {
    # MOST COMMON (74% of addendum PDFs)
    "education_major": {
        "addendum_field": "addendum_educ",
        "crm_field":      "jobeducation",       # confirmed ✅
        "frequency":      0.74,
        "label":          "education requirements / degree field",
    },
    # SOC CODE — pwd_soc_title trigger (43%)
    "pwd_soc_title": {
        "addendum_field": "addendum_soc",
        "crm_field":      None,                 # no dedicated SOC field in CRM — log only
        "frequency":      0.43,
        "label":          "SOC code + occupation title",
        "note":           "No confirmed CRM destination. Content like '43-3031: Bookkeeping...'. Log for review.",
    },
    # SOC CODE — required_occupation trigger (13%, same addendum_soc output)
    "required_occupation": {
        "addendum_field": "addendum_soc",
        "crm_field":      None,                 # same as above
        "frequency":      0.13,
        "label":          "SOC code + occupation title (alternate trigger field)",
        "note":           "Alias for pwd_soc_title addendum. Same addendum_soc content.",
    },
    # JOB DUTIES (12% — less common than assumed)
    "job_duties": {
        "addendum_field": "addendum_job_duties",
        "crm_field":      "adtextnews",         # confirmed ✅ — newspaper ad copy
        "frequency":      0.12,
        "label":          "job duties / newspaper ad copy",
        "note":           "Critical: must NOT write 'Please See Addendum' to adtextnews.",
    },
}

# Fields that do NOT exist in real PDFs (remove from training / routing):
# experience_months, special_requirements, other_skills, soc_code (standalone)


def needs_addendum(value: str) -> bool:
    """Return True if the field value is an addendum trigger phrase."""
    if not value:
        return False
    v = value.lower().strip()
    return any(trigger in v for trigger in ADDENDUM_TRIGGERS)


def resolve_field(primary_value: str, addendum_value: str, fallback: str = "") -> str:
    """
    Resolve the final value for a CRM field.
    - If primary_value is a trigger AND addendum_value has real content → return addendum_value
    - Otherwise return primary_value (or fallback)
    """
    if needs_addendum(primary_value):
        if addendum_value and len(addendum_value.strip()) > 10:
            return addendum_value.strip()
        return fallback or primary_value
    return primary_value or fallback


def route_all_fields(extracted: dict) -> dict:
    """
    Apply addendum routing to all mapped fields.
    Returns dict with CRM field names as keys and resolved values.
    Fields with crm_field=None are included under key 'addendum_log' for review.
    """
    result = {}
    addendum_log = {}

    for extracted_field, routing in FIELD_ROUTING_MAP.items():
        primary_val  = extracted.get(extracted_field, "")
        addendum_val = extracted.get(routing["addendum_field"], "")
        crm_field    = routing["crm_field"]
        resolved     = resolve_field(primary_val, addendum_val)

        if crm_field:
            result[crm_field] = resolved
        elif needs_addendum(primary_val) and addendum_val:
            # No CRM field confirmed — log it for human review
            addendum_log[routing["addendum_field"]] = addendum_val

    if addendum_log:
        result["_addendum_log"] = addendum_log  # caller can inspect

    # Pass through remaining extracted fields unchanged
    skip = set(FIELD_ROUTING_MAP.keys()) | {r["addendum_field"] for r in FIELD_ROUTING_MAP.values()}
    for k, v in extracted.items():
        if k not in skip and k not in result:
            result[k] = v

    return result


def summarize_addenda(extracted: dict) -> list:
    """Return list of addendum detections for logging/debugging."""
    found = []
    for field, routing in FIELD_ROUTING_MAP.items():
        pv = extracted.get(field, "")
        av = extracted.get(routing["addendum_field"], "")
        if needs_addendum(pv):
            found.append({
                "trigger_field":  field,
                "trigger_value":  pv[:80],
                "addendum_field": routing["addendum_field"],
                "content_length": len(av),
                "crm_field":      routing["crm_field"],
                "resolved":       bool(av and len(av) > 10),
                "note":           routing.get("note", ""),
            })
    return found
