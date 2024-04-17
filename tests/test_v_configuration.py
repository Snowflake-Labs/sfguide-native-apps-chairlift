from test_utils import normalize_spaces, session, session_builder
from unittest.mock import MagicMock
from streamlit.testing.v1 import AppTest

def sql_handler(*args):
    query_result = MagicMock()
    stmt = normalize_spaces(args[0])

    if stmt == 'select is_first_time_setup_dismissed from config_data.configuration':
        query_result.collect.return_value = [{'IS_FIRST_TIME_SETUP_DISMISSED': True}]
    elif stmt == 'select enable_warning_generation_task from config_data.configuration limit 1':
        query_result.collect.return_value = [{'ENABLE_WARNING_GENERATION_TASK': True}]
    else:
        raise NotImplementedError(f'"{stmt}"')
    
    return query_result

def test_streamlit_configuration_ui(session):
    session.sql.side_effect = sql_handler

    at = AppTest.from_file('../app/src/ui/v_configuration.py')
    at.run()

    assert not at.exception
    assert at.checkbox[0].label == "Enable warning generation task (⚠️ runs every 60s!)"
    assert at.checkbox[0].value == True
    assert at.button[0].label == 'Generate new warnings (takes a while)'
