import streamlit as st
from snowflake.snowpark.context import get_active_session
import snowflake.permissions as permission

session = get_active_session()

@st.cache_data
def get_app_name() -> str:
    return session.sql("""
        select current_database()
    """).collect()[0]["CURRENT_DATABASE()"]

class _StreamlitClientWithLogger(permission._SnowsightClientBase):
    def __init__(self):
        super().__init__()

    def _send(self, request: permission._Request):
        self.enable_compression = False
        st.write("Original Request")
        st.write(super()._serialize_request(request))
        self.enable_compression = True
        st.write("Compressed Request")
        st.write(super()._serialize_request(request))
        st.experimental_set_query_params(request=super()._serialize_request(request))
