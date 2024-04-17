import streamlit as st
from snowflake.snowpark import Session

@st.cache_data
def get_app_name(_session: Session) -> str:
    return _session.sql("""
        select current_database()
    """).collect()[0]["CURRENT_DATABASE()"]
