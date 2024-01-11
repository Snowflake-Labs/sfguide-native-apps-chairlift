-- sensor data tab: tables and graphs
create or replace
    streamlit ui."Sensor data"
    from 'python/ui' main_file='v_sensor_data.py';

grant usage
    on streamlit ui."Sensor data"
    to application role app_viewer;
