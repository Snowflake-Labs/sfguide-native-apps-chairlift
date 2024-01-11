-- configuration tab: only available to app_admin
create or replace
    streamlit ui."Configuration"
    from 'python/ui' main_file='v_configuration.py';

grant usage
    on streamlit ui."Configuration"
    to application role app_admin;
