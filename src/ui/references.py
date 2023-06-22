from dataclasses import dataclass
import json
from typing import List

import streamlit as st
from snowflake.snowpark.context import get_active_session
import snowflake.permissions as permission

from util import get_app_name

session = get_active_session()

@dataclass
class Reference:
    name: str
    label: str
    description: str
    bound_alias: str

def render_request_reference_button(ref: Reference, button_type: str = "primary") -> None:
    """
    :param type: "primary" or "secondary"
    """
    st.button(
        f"Select {ref.name} table ↗",
        on_click=permission.request_reference,
        args=[ref.name],
        key=ref.name,
        type=button_type
    )

def get_app_references(show_json=False) -> List[Reference]:
    app_name = get_app_name()

    refs_json = session.sql(f"select system$get_reference_definitions('{app_name}') as REFS_JSON").collect()[0]["REFS_JSON"]
    refs = json.loads(refs_json)

    if show_json:
        pretty_json = json.dumps(refs, sort_keys=True, indent=4)
        with st.expander("Output of `system$get_reference_definitions`"):
            st.code(pretty_json, language="javascript")

    references = []
    for row in refs:
        bound_alias = row["bindings"][0]["alias"] if row["bindings"] else None
        references.append(
            Reference(row["name"], row["label"], row["description"], bound_alias)
        )

    return references

def render_reference_pane(ref: Reference) -> None:
    st.divider()
    if ref.bound_alias:
        st.caption(f"*{ref.label}* binding exists ✅")
        # TODO: we could go further and validate the table shape
    else:
        col1, col2 = st.columns([0.7, 0.3])
        with col1: st.subheader(f"{ref.label}")
        with col2: st.error('Unbound reference', icon="🚨")
        st.caption(f"{ref.description}")
        render_request_reference_button(ref)
