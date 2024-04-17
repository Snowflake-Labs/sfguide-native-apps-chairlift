from dataclasses import dataclass
from typing import List, Optional, Tuple, Any
import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st
from snowflake.snowpark import Session

from ui_common import warnings_banner
from first_time_setup import get_is_first_time_setup_dismissed, \
    render as render_first_time_setup
from chairlift_data import Machine, SensorType, get_machines, \
    get_sensor_types

@dataclass
class TimestampFilter:
    date: dt.date
    time: dt.time

    def to_datetime(self):
        return dt.datetime.combine(self.date, self.time)

    def to_iso(self):
        return self.to_datetime().isoformat()

    def to_unix_timestamp(self):
        """ Returns an integer epoch timestamp (seconds) """
        return int(self.to_datetime().timestamp())


@dataclass
class Filters:
    machines: List[Machine]
    sensor_types: List[SensorType]
    min_ts: Optional[TimestampFilter]
    max_ts: Optional[TimestampFilter]
    only_alerts: Optional[bool]


st.set_page_config(layout="wide")


@st.cache_data
def get_sensor_data(
    _session: Session,
    filters: Optional[Filters] = None
) -> pd.DataFrame:
    """
    Fetches sensor data from snowflake, with optional filtering.
    Uses references defined in the app manfiest.yml to query consumer data directly.
    """

    where_predicates: List[str] = []
    if filters:
        if filters.machines:
            predicates = [f"sensor.machine_uuid = '{machine.uuid}'" for machine in filters.machines]
            or_clause = ' or '.join(predicates)
            where_predicates.append(f"({or_clause})")
        
        if filters.sensor_types:
            predicates = [f"sensor.sensor_type_id = {sensor_type.id}" for sensor_type in filters.sensor_types]
            or_clause = ' or '.join(predicates)
            where_predicates.append(f"({or_clause})")
        
        if filters.only_alerts:
            where_predicates.append(f"status <> ''")

        if filters.min_ts:
            min_epoch_sec = filters.min_ts.to_unix_timestamp()
            where_predicates.append(f"reading.reading_time >= TO_TIMESTAMP({min_epoch_sec})")

        if filters.max_ts:
            max_epoch_sec = filters.max_ts.to_unix_timestamp()
            where_predicates.append(f"reading.reading_time <= TO_TIMESTAMP({max_epoch_sec})")

    where_clause = f"where {' and '.join(where_predicates)}" if where_predicates else ""

    return _session.sql(f"""
        select 
            reading.reading_time as ts,
            machine.name as machine_name,
            sensor.name as sensor_name,
            reading.reading as value,
            case
                when reading.reading < sensor_range.min_range then '⚠️ LOW'
                when reading.reading > sensor_range.max_range then '⚠️ HIGH'
                else ''
            end as status

        from reference('SENSOR_READINGS') reading
        inner join reference('SENSORS') sensor
            on sensor.uuid = reading.sensor_uuid
        inner join reference('MACHINES') machine
            on machine.uuid = sensor.machine_uuid
        inner join shared_content.SENSOR_RANGES sensor_range
            on sensor_range.id = sensor.sensor_type_id
    
        {where_clause}

        order by
            ts desc,
            machine_uuid asc,
            sensor_name asc
    """).to_pandas()

def render_common_filters(session: Session):
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
    only_alerts = col2.checkbox('Hide in-spec readings')

    min_ts: Optional[TimestampFilter] = None
    max_ts: Optional[TimestampFilter] = None
    if enable_ts_filter:
        # when we enable, we'll do the past 2 days by default
        col1, col2, col3, col4 = st.columns(4)
        min_date = col1.date_input('From date', max_value=dt.date.today(), value=dt.date.today() - dt.timedelta(days=1))
        min_time = col2.time_input('From time', value=dt.time(0, 0, 0))
        min_ts = TimestampFilter(min_date, min_time)
        max_date = col3.date_input('To date', min_value=min_date, value=dt.date.today())
        max_time = col4.time_input('To time', value=dt.time(23, 59, 59)) # FIXME: might miss last second of day!
        max_ts = TimestampFilter(max_date, max_time)

    return Filters(machines, sensor_types, min_ts, max_ts, only_alerts)

def render_table(_filters: Filters, sensor_data: pd.DataFrame):
    st.dataframe(
        sensor_data,
        use_container_width=True
    )

def warning_line(y: float):
    return alt.Chart(
        pd.DataFrame({'y': [y]})
    ).mark_rule(
        color='red',
        strokeDash=[5, 5],  # 5px dash, 5px gap
    ).encode(y='y')

def render_graph(session: Session, filters: Filters, sensor_data: pd.DataFrame):
    # one chart for each sensor type, with min / max lines
    charts = []
    for sensor_type in get_sensor_types(session):
        # if there's no data for this graph, don't generate it
        if len(sensor_data[(sensor_data['SENSOR_NAME'] == sensor_type.name)]) == 0:
            continue

        # adjust chart scale to have 20% space above and below the expected range
        buffer = 0.2 * (sensor_type.max_range - sensor_type.min_range)
        scale_min = sensor_type.min_range - buffer
        scale_max = sensor_type.max_range + buffer

        title=sensor_type.name
        machine_readings = alt.Chart(sensor_data, title=title).mark_line(clip=True).encode(
            x=alt.X('TS:T', title='Timestamp'),
            y=alt.Y('VALUE:Q', title='Reading', scale=alt.Scale(zero=False, domain=(scale_min, scale_max))),
            color=alt.Color('MACHINE_NAME:N', title='Machine'),
        ).transform_filter(
            alt.FieldEqualPredicate(
                field='SENSOR_NAME',
                equal=sensor_type.name,
            )
        )

        # N.B. we have altair v4.1.0, so no alt.datum
        min_line = warning_line(sensor_type.min_range)
        max_line = warning_line(sensor_type.max_range)
        chart = (machine_readings + min_line + max_line)
        charts.append(chart)

    # arrange charts into up to columns
    if charts:
        MAX_COLUMNS = 3
        columns = st.columns(min(MAX_COLUMNS, len(charts)))
        for i, chart in enumerate(charts):
            col = columns[i % len(columns)]
            col.altair_chart(
                chart,
                use_container_width=True,
            )

def render(session: Session):
    warnings_banner(session)
    st.header("Sensor data")
    filters = render_common_filters(session)
    sensor_data = get_sensor_data(session, filters)

    graph_tab, table_tab = st.tabs(["Plotted over time", "Raw sensor readings"])
    with graph_tab: render_graph(session, filters, sensor_data)
    with table_tab: render_table(filters, sensor_data)


if __name__ == "__main__":
    session = Session.builder.getOrCreate()
    if not get_is_first_time_setup_dismissed(session):
        render_first_time_setup(session)
    else:
        render(session)
