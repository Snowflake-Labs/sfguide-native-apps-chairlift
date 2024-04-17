from dataclasses import dataclass
from typing import List
from snowflake.snowpark import Session

import streamlit as st

@dataclass
class Machine:
    uuid: str
    name: str

@st.cache_data
def get_machines(_session: Session) -> List[Machine]:
    machine_tuples = _session.sql(f"""
        select UUID, NAME from reference('MACHINES')
    """).collect()
    return [Machine(t["UUID"], t["NAME"]) for t in machine_tuples]

@dataclass
class SensorType:
    id: int
    name: str
    min_range: float
    max_range: float

@st.cache_data
def get_sensor_types(_session: Session) -> List[SensorType]:
    sensor_type_tuples = _session.sql(f"""
        select ID, NAME, MIN_RANGE, MAX_RANGE
        from shared_content.SENSOR_TYPES_VIEW
    """).collect()
    return [
        SensorType(t["ID"], t["NAME"], t["MIN_RANGE"], t["MAX_RANGE"])
        for t in sensor_type_tuples
    ]
