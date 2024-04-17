from test_utils import normalize_spaces, session, session_builder
from unittest.mock import MagicMock
from streamlit.testing.v1 import AppTest
import pandas as pd
import numpy as np
import re

def sql_handler(*args):
    query_result = MagicMock()
    stmt = normalize_spaces(args[0])

    if stmt == "select is_first_time_setup_dismissed from config_data.configuration":
        query_result.collect.return_value = [{'IS_FIRST_TIME_SETUP_DISMISSED': True}]
    elif stmt == "select count(*) as WARNING_COUNT from warnings_data.warnings where ACKNOWLEDGED = false":
        query_result.collect.return_value = [{'WARNING_COUNT': 2}]
    elif stmt == "select UUID, NAME from reference('MACHINES')":
        query_result.collect.return_value = [
            {'UUID': '1234-abcd-1234', 'NAME': 'Chairlift #2'},
            {'UUID': '4321-dcba-4321', 'NAME': 'Chairlift #3'}
        ]
    elif stmt == "select ID, NAME, MIN_RANGE, MAX_RANGE from shared_content.SENSOR_TYPES_VIEW":
        query_result.collect.return_value = [
            {'ID': 'sensorTypeId1', 'NAME': 'Chairlift Load', 'MIN_RANGE': 100, 'MAX_RANGE': 200},
            {'ID': 'sensorTypeId2', 'NAME': 'Chairlift Vibration', 'MIN_RANGE': 2, 'MAX_RANGE': 50}
        ]
    elif re.match(r"select warning.sensor_uuid as SENSOR_UUID, warning.reading_time as READING_TIME, concat\(to_date\(warning.reading_time\), ' ', to_time\(warning.reading_time\)\) as readable_time, machine.name as machine_name, sensor.name as sensor_name, warning.reading as reading, warning.reason as reason.*", stmt):
        query_result.to_pandas.return_value = pd.DataFrame(
            np.array([
                ['sensor_uuid_3', '2024-04-01 09:37:34', '2024-04-01 09:37:34', 'Chairlift #3', 'Chairlift Vibration', 38, 'SENSOR_SERVICE_DUE'],
                ['sensor_uuid_2', '2024-04-01 08:36:22', '2024-04-01 08:36:22', 'Chairlift #2', 'Chairlift Load', 45, 'SENSOR_READING_OUT_OF_RANGE']
            ]),
            columns=['SENSOR_UUID', 'READING_TIME', 'READABLE_TIME', 'MACHINE_NAME', 'SENSOR_NAME', 'READING', 'REASON']
        )
    else:
        raise NotImplementedError(f'"{stmt}"')
    
    return query_result

def test_streamlit_dashboard_ui(session):
    session.sql.side_effect = sql_handler

    at = AppTest.from_file('../app/src/ui/v_dashboard.py')
    at.run()

    assert not at.exception
    assert at.warning[0].value == 'There are 2 new unacknowledged warnings.'
    assert at.multiselect('machines').options == ['Chairlift #2', 'Chairlift #3']
    assert at.multiselect('sensorTypes').options == ['Chairlift Load', 'Chairlift Vibration']

    assert [col.caption.values[0] for col in at.columns[6:12]] == ['READING TIME', 'MACHINE NAME', 'SENSOR NAME', 'READING', 'REASON', 'ACKNOWLEDGE']
    assert [col.markdown.values[0] for col in at.columns[12:17]] == ['2024-04-01 09:37:34', 'Chairlift #3', 'Chairlift Vibration', '38', 'SENSOR_SERVICE_DUE']
    assert len(at.columns[17].checkbox) == 1
    assert [col.markdown.values[0] for col in at.columns[18:23]] == ['2024-04-01 08:36:22', 'Chairlift #2', 'Chairlift Load', '45', 'SENSOR_READING_OUT_OF_RANGE']
    assert len(at.columns[23].checkbox) == 1
