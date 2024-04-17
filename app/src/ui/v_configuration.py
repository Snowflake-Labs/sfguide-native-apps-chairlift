import streamlit as st
from first_time_setup import get_is_first_time_setup_dismissed, \
    render as render_first_time_setup
from snowflake.snowpark import Session

def check_warning_task_enabled(session: Session):
    is_warning_task_enabled = session.sql(f"""
        select enable_warning_generation_task from config_data.configuration limit 1
    """).collect()[0]['ENABLE_WARNING_GENERATION_TASK']
    return is_warning_task_enabled

def update_warning_task_enabled(session: Session, should_enable):
    session.sql(f"""
        call warnings_code.update_warning_check_task_status({should_enable})
    """).collect()

def generate_warnings_once(session: Session):
    result = session.sql(f"""
        call warnings_code.check_warnings()
    """).collect()

def render(session):
    st.header("Configuration")
    st.caption("""
        When new sensor data is created, it needs to be scanned for values
        that are out-of-bounds. A warning will be created for each discovered
        reading that does not fall within the manufacturer's specified range.
        Note that enabling the warning generation task can consume a lot of
        credits in your Snowflake account; the warning generation logic can
        instead be manually triggered by clicking the button below.
    """)

    # warning task
    is_warning_task_enabled = check_warning_task_enabled(session)
    new_value = st.checkbox(
        label="Enable warning generation task (⚠️ runs every 60s!)",
        value=is_warning_task_enabled,
        key='warning_task_enabled'
    )
    if is_warning_task_enabled != new_value:
        update_warning_task_enabled(session, new_value)
        st.experimental_rerun()

    # one-time warning generation
    st.button(
        label="Generate new warnings (takes a while)",
        on_click=lambda: generate_warnings_once(session),
        disabled=is_warning_task_enabled,
    )

if __name__ == "__main__":
    session = Session.builder.getOrCreate()
    if not get_is_first_time_setup_dismissed(session):
        render_first_time_setup(session)
    else:
        render(session)
