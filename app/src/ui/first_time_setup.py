import streamlit as st
from snowflake.snowpark import Session
from references import get_app_references, render_reference_pane
import snowflake.permissions as permission

APP_CONFIG_TABLE = "config_data.configuration"
PRIVILEGES = ["EXECUTE TASK"]

def set_is_first_time_setup_dismissed(session: Session, value):
    session.sql(f"""
        call warnings_code.create_warning_check_task()
    """).collect()
    #TODO: This will start the warnings generation task
    session.sql(f"""
        update {APP_CONFIG_TABLE} set is_first_time_setup_dismissed={value}
    """).collect()

def get_is_first_time_setup_dismissed(session: Session):
    return session.sql(f"""
        select is_first_time_setup_dismissed from {APP_CONFIG_TABLE}
    """).collect()[0]["IS_FIRST_TIME_SETUP_DISMISSED"]

def request_account_privileges():
    st.caption(f"The following privileges are needed")
    privileges = st.code(','.join(PRIVILEGES), language="markdown")
    st.button("Request Privileges", on_click=permission.request_account_privileges, args=[PRIVILEGES])

def render(session: Session):
    st.header("First-time setup")
    st.caption("""
        Follow the instructions below to set up your application.
        Once you have completed the steps, you will be able to continue to the main dashboard.
    """)
    for ref in get_app_references(session):
        render_reference_pane(ref)

        # don't overwhelm the user with multiple actions to take
        if not ref.bound_alias: return

    st.divider()
    try:
        res = permission.get_missing_account_privileges(PRIVILEGES)
        if res and len(res) > 0:
            request_account_privileges()
            return
        else:
            st.caption(f"*Privileges* are granted ✅")
    except Exception as e:
        st.write(e)
        return

    # if we got here, all references were bound!
    st.divider()
    col1, col2 = st.columns([0.65, 0.35])
    col1.caption("All first-time setup tasks have been completed! 🎉")
    col2.button(
        f"Continue to app",
        on_click=lambda: set_is_first_time_setup_dismissed(session, True),
        type="primary"
    )
