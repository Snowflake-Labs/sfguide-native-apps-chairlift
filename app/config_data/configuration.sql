-- this table will have exactly one row at all times, and will be
-- the state of the application (durable between runs / upgrades)
create
    table if not exists config_data.configuration (
        is_first_time_setup_dismissed boolean not null
    );

execute immediate $$
    begin
        alter table config_data.configuration
            add column enable_warning_generation_task boolean default false;
    exception
        when other then
            return 1;
    end;
$$
;

-- initialize the table with exactly one row, if it doesn't already have one
insert into config_data.configuration
    (is_first_time_setup_dismissed, enable_warning_generation_task)
select
    false, false
where not exists (select 1 from config_data.configuration limit 1);

-- app admin can update app config from outside streamlit if they like
grant select, update on config_data.configuration to application role app_admin;
