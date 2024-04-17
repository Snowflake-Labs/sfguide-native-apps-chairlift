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
    elif re.match(r"select reading.reading_time as ts, machine.name as machine_name, sensor.name as sensor_name, reading.reading as value, case when reading.reading < sensor_range.min_range then '⚠️ LOW' when reading.reading > sensor_range.max_range then '⚠️ HIGH' else '' end as status.*", stmt):
        query_result.to_pandas.return_value = pd.DataFrame(
            np.array([
                ['2024-04-01 09:01:00', 'Chairlift #3', 'Chairlift Load', 99, '⚠️ LOW'],
                ['2024-04-01 08:02:00', 'Chairlift #3', 'Chairlift Load', 97, '⚠️ LOW'],
                ['2024-04-01 07:03:00', 'Chairlift #3', 'Chairlift Load', 95, '⚠️ LOW'],
                ['2024-04-01 08:04:00', 'Chairlift #2', 'Chairlift Vibration', 45, ''],
                ['2024-04-01 07:05:00', 'Chairlift #2', 'Chairlift Vibration', 51, '⚠️ HIGH'],
                ['2024-04-01 06:06:00', 'Chairlift #2', 'Chairlift Vibration', 47, '']
            ]),
            columns=['TS', 'MACHINE_NAME', 'SENSOR_NAME', 'VALUE', 'STATUS']
        )
    else:
        raise NotImplementedError(f'"{stmt}"')
    
    return query_result

def test_streamlit_sensor_data_ui(session):
    session.sql.side_effect = sql_handler

    at = AppTest.from_file('../app/src/ui/v_sensor_data.py')
    at.run()

    assert not at.exception
    assert at.warning[0].value == 'There are 2 new unacknowledged warnings.'
    assert at.multiselect('machines').options == ['Chairlift #2', 'Chairlift #3']
    assert at.multiselect('sensorTypes').options == ['Chairlift Load', 'Chairlift Vibration']

    assert len(at.tabs) == 2
    assert at.tabs[0].label == 'Plotted over time'
    assert len(at.tabs[0].columns) == 2 # 2 columns for 2 charts
    assert at.tabs[1].label == 'Raw sensor readings'
    assert (at.tabs[1].dataframe[0].value[:].values == [
        ['2024-04-01 09:01:00', 'Chairlift #3', 'Chairlift Load', '99', '⚠️ LOW'],
        ['2024-04-01 08:02:00', 'Chairlift #3', 'Chairlift Load', '97', '⚠️ LOW'],
        ['2024-04-01 07:03:00', 'Chairlift #3', 'Chairlift Load', '95', '⚠️ LOW'],
        ['2024-04-01 08:04:00', 'Chairlift #2', 'Chairlift Vibration', '45', ''],
        ['2024-04-01 07:05:00', 'Chairlift #2', 'Chairlift Vibration', '51', '⚠️ HIGH'],
        ['2024-04-01 06:06:00', 'Chairlift #2', 'Chairlift Vibration', '47', '']
    ]).all()
