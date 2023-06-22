import streamlit as st
from snowflake.snowpark.context import get_active_session
from first_time_setup import get_is_first_time_setup_dismissed, \
    render as render_first_time_setup

session = get_active_session()

def check_warning_task_enabled():
    is_warning_task_enabled = session.sql(f"""
        select enable_warning_generation_task from config_data.configuration limit 1
    """).collect()[0]['ENABLE_WARNING_GENERATION_TASK']
    return is_warning_task_enabled

def update_warning_task_enabled(should_enable):
    session.sql(f"""
        call warnings_code.update_warning_check_task_status({should_enable})
    """).collect()

def render():
    st.header("Configuration")
    is_warning_task_enabled = check_warning_task_enabled()
    col1, col2 = st.columns([0.5, 0.5])
    col1.caption("Enable warning generation task")
    with col2:
        new_value = st.checkbox(label='', value=is_warning_task_enabled, key='warning_task_enabled')
        if is_warning_task_enabled != new_value:
            update_warning_task_enabled(new_value)

if __name__ == "__main__":
    if not get_is_first_time_setup_dismissed():
        render_first_time_setup()
    else:
        render()
