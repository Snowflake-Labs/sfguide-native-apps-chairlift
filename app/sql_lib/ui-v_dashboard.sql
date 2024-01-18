
-- dashboard tab: warnings and acknowledgment
create or replace
    streamlit ui."Dashboard"
    from 'src/ui' main_file='v_dashboard.py';

grant usage
    on streamlit ui."Dashboard"
    to application role app_viewer;
