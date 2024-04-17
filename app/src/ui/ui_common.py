import urllib.parse

import streamlit as st
from snowflake.snowpark import Session

from util import get_app_name

def warnings_banner(session: Session):
    warning_count = session.sql(f"""
        select count(*) as WARNING_COUNT from warnings_data.warnings where ACKNOWLEDGED = false
    """).collect()[0]["WARNING_COUNT"]
    if warning_count > 0:
        st.warning(f'There are {warning_count} new unacknowledged warnings.', icon="⚠️")

def link_to_streamlit(session: Session, text, streamlit_name, schema="UI"):
    """ N.B. all non-quoted identifiers must be UPPERCASE """
    # FIXME: this does not work unfortunately, but leaving it in on the off chance we can fix it
    url_quoted_name = urllib.parse.quote(streamlit_name)
    hash_location = f"#/apps/application/{get_app_name(session)}/schema/{schema}/streamlit/{url_quoted_name}"
    st.markdown(f"[{text}]({hash_location})")
