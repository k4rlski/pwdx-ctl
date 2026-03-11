"""
addendum_ctl — Addendum trigger detection and field routing for ETA-9141 PWD extraction.
Issue #2: https://github.com/k4rlski/pwdx-ctl/issues/2
"""
from .router import needs_addendum, resolve_field, route_all_fields, ADDENDUM_TRIGGERS, FIELD_ROUTING_MAP
