"""Tool registry.

Workflow executors import from here so agent wiring is declarative.
"""
from .crm_read import SCHEMA as CRM_READ_SCHEMA, crm_read_account
from .crm_write_contact import SCHEMA as CRM_WRITE_SCHEMA, crm_write_contact
from .send_email import SCHEMA as SEND_EMAIL_SCHEMA, send_email
from .web_search import SCHEMA as WEB_SEARCH_SCHEMA, web_search

READ_ONLY_TOOLS = {
    "crm_read_account": (crm_read_account, CRM_READ_SCHEMA),
    "web_search": (web_search, WEB_SEARCH_SCHEMA),
}

SIDE_EFFECT_TOOLS = {
    "crm_write_contact": (crm_write_contact, CRM_WRITE_SCHEMA),
    "send_email": (send_email, SEND_EMAIL_SCHEMA),
}

ALL_TOOLS = {**READ_ONLY_TOOLS, **SIDE_EFFECT_TOOLS}
