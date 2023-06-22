import urllib.parse

import streamlit as st
from snowflake.snowpark.context import get_active_session

from util import get_app_name

session = get_active_session()

def warnings_banner():
    warning_count = session.sql(f"""
        select count(*) as WARNING_COUNT from warnings_data.warnings where ACKNOWLEDGED = false
    """).collect()[0]["WARNING_COUNT"]
    if warning_count > 0:
        st.warning(f'There are {warning_count} new unacknowledged warnings.', icon="⚠️")

def link_to_streamlit(text, streamlit_name, schema="UI"):
    """ N.B. all non-quoted identifiers must be UPPERCASE """
    # FIXME: this does not work unfortunately, but leaving it in on the off chance we can fix it
    url_quoted_name = urllib.parse.quote(streamlit_name)
    hash_location = f"#/apps/application/{get_app_name()}/schema/{schema}/streamlit/{url_quoted_name}"
    st.markdown(f"[{text}]({hash_location})")
