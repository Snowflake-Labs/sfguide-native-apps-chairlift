from typing import List, Optional, Tuple
import datetime as dt
import streamlit as st
from snowflake.snowpark import Session

from ui_common import warnings_banner
from first_time_setup import get_is_first_time_setup_dismissed, \
    render as render_first_time_setup
from chairlift_data import Machine, SensorType, get_machines, \
    get_sensor_types

def get_warning_data(
        session: Session,
        machines: Optional[List[Machine]] = None,
        sensor_types: Optional[List[SensorType]] = None,
        min_ts: Optional[Tuple[dt.date, dt.time]] = None,
        max_ts: Optional[Tuple[dt.date, dt.time]] = None,
        acknowledged: Optional[bool] = False
) -> None:
    """
    Fetches sensor data from snowflake, with optional filtering.
    Uses references defined in the app manfiest.yml to query consumer data directly.
    """

    where_predicates: List[str] = []

    if machines:
        predicates = [f"sensor.machine_uuid = '{machine.uuid}'" for machine in machines]
        or_clause = ' or '.join(predicates)
        where_predicates.append(f"({or_clause})")

    if sensor_types:
        predicates = [f"sensor.sensor_type_id = {sensor_type.id}" for sensor_type in sensor_types]
        or_clause = ' or '.join(predicates)
        where_predicates.append(f"({or_clause})")

    if min_ts:
        min_epoch_sec = int(dt.datetime.combine(min_ts[0], min_ts[1]).timestamp())
        where_predicates.append(f"warning.reading_time >= to_timestamp({min_epoch_sec})")

    if max_ts:
        max_epoch_sec = int(dt.datetime.combine(max_ts[0], max_ts[1]).timestamp())
        where_predicates.append(f"warning.reading_time <= to_timestamp({max_epoch_sec})")

    where_predicates.append(f"warning.acknowledged = {acknowledged}")

    where_clause = f"where {' and '.join(where_predicates)}" if where_predicates else ""

    return session.sql(f"""
        select 
            warning.sensor_uuid as SENSOR_UUID, 
            warning.reading_time as READING_TIME, 
            concat(to_date(warning.reading_time), ' ', to_time(warning.reading_time)) as readable_time, 
            machine.name as machine_name, 
            sensor.name as sensor_name, 
            warning.reading as reading, 
            warning.reason as reason
        from warnings_data.warnings warning 
        inner join reference('SENSORS') sensor 
            on sensor.uuid = warning.sensor_uuid 
        inner join reference('MACHINES') machine 
            on machine.uuid = sensor.machine_uuid 

        {where_clause}

        order by
            reading_time desc,
            machine_uuid asc,
            sensor_name asc
        
        limit 20
    """).to_pandas()

def render(session: Session, selected_rows):
    st.set_page_config(layout="wide")
    warnings_banner(session)
    st.header("Warnings")
    st.button("Dismiss all", on_click=lambda: dismiss_all(session))

    st.caption("Showing first 20")
    col1, col2 = st.columns([0.5, 0.5])
    acknowledged_filter = col1.checkbox('Show acknowledged warnings')

    if not acknowledged_filter:
        # filters
        col1, col2 = st.columns([0.5, 0.5])
        machines = col1.multiselect(
            'Filter by machine',
            options=get_machines(session),
            format_func=lambda machine: machine.name,
            key='machines'
        )
        sensor_types = col2.multiselect(
            'Filter by sensor type',
            options=get_sensor_types(session),
            format_func=lambda sensor_type: sensor_type.name,
            key='sensorTypes'
        )

        col1, col2 = st.columns([0.5, 0.5])
        enable_ts_filter = col1.checkbox('Filter by date...')

        if enable_ts_filter:
            # when we enable, we'll do the past 2 days by default
            col1, col2, col3, col4 = st.columns(4)
            from_date = col1.date_input('From date', max_value=dt.date.today(), value=dt.date.today() - dt.timedelta(days=1))
            from_time = col2.time_input('From time', value=dt.time(0, 0, 0))
            to_date = col3.date_input('To date', min_value=from_date, value=dt.date.today())
            to_time = col4.time_input('To time', value=dt.time(23, 59, 59)) # FIXME: might miss last second of day!
    else:
        machines = None
        sensor_types = None
        enable_ts_filter = None

    warning_data = get_warning_data(
        session=session,
        machines=machines,
        sensor_types=sensor_types,
        min_ts=(from_date, from_time) if enable_ts_filter else None,
        max_ts=(to_date, to_time) if enable_ts_filter else None,
        acknowledged=acknowledged_filter
    )

    cols_width = [0.15,0.10,0.15,0.10,0.20,0.15]

    col1, col2, col3, col4, col5, col6 = st.columns(cols_width);
    select_all = False
    with col1:
        st.caption('READING TIME')

    with col2:
        st.caption('MACHINE NAME')

    with col3:
        st.caption('SENSOR NAME')

    with col4:
        st.caption('READING')

    with col5:
        st.caption('REASON')

    with col6:
        st.caption('ACKNOWLEDGE')
        if not acknowledged_filter:
            select_all = st.checkbox(label='Select All', key='selectAll')
            st.button("Dismiss", on_click=lambda: dismiss_selected(session, selected_rows))

    for index, row in warning_data.iterrows():
        col1, col2, col3, col4, col5, col6 = st.columns(cols_width);

        with col1:
            st.write(row['READABLE_TIME'])

        with col2:
            st.write(row['MACHINE_NAME'])

        with col3:
            st.write(row['SENSOR_NAME'])

        with col4:
            st.write(row['READING'])

        with col5:
            st.write(row['REASON'])

        with col6:
            # TODO possible duplicate IDs
            id = row['SENSOR_UUID'] + '/' + str(row['READABLE_TIME'])
            if not acknowledged_filter:
                args = [row['SENSOR_UUID'], row['READING_TIME'], id]
                val = st.checkbox(label='', value=select_all, key=id, args=args)
                if val:
                    selected_rows[id] = args
                elif id in selected_rows:
                    del selected_rows[id]
            else:
                st.checkbox(label='', value=True, disabled=True, key=id)
        st.divider()

    st.session_state['selected_rows'] = selected_rows

def dismiss_selected(session: Session, selected_rows):
    for x in selected_rows.keys():
        val = selected_rows[x]
        session.sql(f"""
            update warnings_data.warnings set acknowledged = true where sensor_uuid = '{val[0]}' and reading_time = '{val[1]}'
        """).collect()
    st.session_state['selected_rows'] = {}

def dismiss_all(session: Session):
    session.sql(f"update warnings_data.warnings set acknowledged = true").collect()
    st.session_state['selected_rows'] = {}

if __name__ == "__main__":
    session = Session.builder.getOrCreate()
    if 'selected_rows' not in st.session_state:
        st.session_state['selected_rows'] = {}

    selected_rows = st.session_state['selected_rows']

    if not get_is_first_time_setup_dismissed(session):
        render_first_time_setup(session)
    else:
        render(session, selected_rows)
