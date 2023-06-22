-- this app exposes 2 application roles: admin and viewer
create application role if not exists app_admin;
create application role if not exists app_viewer;

-- viewer permissions are a subset of those for the admin
grant application role app_viewer to application role app_admin;

-- the ui schema holds all streamlits
create or replace schema ui;

    grant usage on schema ui to application role app_viewer;

    -- we sometimes use quoted identifiers as streamlit names
    -- are used as tab names in Snowsight's app view

    -- dashboard tab: warnings and acknowledgment
    create or replace
        streamlit ui."Dashboard"
        from 'ui' main_file='v_dashboard.py';

    grant usage
        on streamlit ui."Dashboard"
        to application role app_viewer;

    -- sensor data tab: tables and graphs
    create or replace
        streamlit ui."Sensor data"
        from 'ui' main_file='v_sensor_data.py';

    grant usage
        on streamlit ui."Sensor data"
        to application role app_viewer;

    -- configuration tab: only available to app_admin
    create or replace
        streamlit ui."Configuration"
        from 'ui' main_file='v_configuration.py';

    grant usage
        on streamlit ui."Configuration"
        to application role app_admin;

-- simple generic methods to register callbacks
create or alter versioned schema config_code;

    grant usage on schema config_code to application role app_admin;

    -- this callback is used by the UI to ultimately bind a reference that expects one value
    create or replace procedure config_code.register_single_callback(ref_name string, operation string, ref_or_alias string)
    returns string
    language sql
    as $$
        begin
            case (operation)
                when 'ADD' then
                    select system$set_reference(:ref_name, :ref_or_alias);
                when 'REMOVE' then
                    select system$remove_reference(:ref_name);
                when 'CLEAR' then
                    select system$remove_reference(:ref_name);
                else
                    return 'Unknown operation: ' || operation;
            end case;
            system$log('debug', 'register_single_callback: ' || operation || ' succeeded');
            return 'Operation ' || operation || ' succeeded';
        end;
    $$;

    grant usage on procedure config_code.register_single_callback(string, string, string)
        to application role app_admin;

-- the config data schema holds configuration data
-- we create a non-versioned schema "if not exists"
-- so that we do not clobber state whenever we upgrade the app
create schema if not exists config_data;

    grant usage on schema config_data to application role app_admin;

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

-- we need two views for each table we want to share from the provider through the app:
-- one set of views live in the package schema; the other set of views are defined here
create or alter versioned schema shared_content;

    -- View for sensor types full data
    create or replace view shared_content.sensor_types_view
        as select * from package_shared.sensor_types_view;

    -- View for sensor reading ranges
    create or replace view shared_content.sensor_ranges
        as select * from package_shared.sensor_ranges;

    -- View for sensor service scheduling
    create or replace view shared_content.sensor_service_schedules
        as select * from package_shared.sensor_service_schedules;

-- non-versioned schema to prevent data loss on upgrade
-- we'll also store our task(s) here
create schema if not exists warnings_data;

    grant usage on schema warnings_data to application role app_admin;

    --This table keep track of what was the last reading that was processed for warnings.
    create table if not exists warnings_data.warnings_reading_cursor (
        last_reading_ts timestamp not null
    );

    grant select on table warnings_data.warnings_reading_cursor to application role app_admin;

    create table if not exists warnings_data.warnings (
        sensor_uuid varchar,
        reading int,
        reading_time timestamp,
        reason varchar,
        acknowledged boolean default false,
        created_at timestamp default current_timestamp()
    );

    grant select on table warnings_data.warnings to application role app_admin;

-- versioned schema to hold our stored procedures
create or alter versioned schema warnings_code;

    -- check for warnings in reading table
    create or replace procedure warnings_code.check_warnings()
    returns varchar
    language sql
    as
    $$
        declare
            warning_processed INT default 0;
            warning_reading_cursor_ts timestamp default dateadd(year, -1, current_timestamp());
            c1 CURSOR FOR
                select id, uuid, reading_time, reading, installation_date, last_service_date, min_range, max_range,
                        service_interval_count, service_interval_unit, lifetime_count, lifetime_unit
                    from REFERENCE('sensor_readings') sre
                    join REFERENCE('sensors') s on s.uuid = sensor_uuid
                    join SHARED_CONTENT.SENSOR_TYPES_VIEW stv on s.sensor_type_id = stv.id
                    where reading_time > ?
                    order by reading_time asc;
        begin
            system$log_info('check_warnings() stored procedure started...');
            select count(*) into :warning_processed from warnings_data.warnings_reading_cursor;
            if (warning_processed > 0) then
                select last_reading_ts into :warning_reading_cursor_ts from warnings_data.warnings_reading_cursor;
            end if;
            open c1 using(warning_reading_cursor_ts);
            FOR record IN c1 DO
                let reading_time datetime default record.reading_time;
                let uuid varchar default record.uuid;
                let min_range integer default record.min_range;
                let max_range integer default record.max_range;
                let reading integer default record.reading;
                let installation_date date default record.installation_date;
                let last_service_date date default record.last_service_date;
                let service_interval_count integer default record.service_interval_count;
                let service_interval_unit varchar default record.service_interval_unit;
                let lifetime_count integer default record.lifetime_count;
                let lifetime_unit varchar default record.lifetime_unit;
                let next_service_date date default dateadd(:service_interval_unit,:service_interval_count,:last_service_date);
                let next_replacement_date date default dateadd(:lifetime_unit,:lifetime_count,:installation_date);
                let warning boolean default false;
                let reason varchar default '';
                if (next_replacement_date < CURRENT_DATE()) then
                    warning := true;
                    reason := 'SENSOR_LIFETIME_EXPIRED';
                elseif (next_service_date < CURRENT_DATE()) then
                    warning := true;
                    reason := 'SENSOR_SERVICE_DUE';
                end if;
                if (reading < min_range) then
                    warning := true;
                    reason := 'SENSOR_READING_OUT_OF_RANGE';
                elseif (reading > max_range) then
                    warning := true;
                    reason := 'SENSOR_READING_OUT_OF_RANGE';
                elseif (reading is null) then
                    warning := true;
                    reason := 'SENSOR_NOT_SENDING_DATA';
                end if;
                if (warning = true) then
                    system$log_info(concat('New Warning: sensor_uuid:', :uuid, ', reason:', :reason, ', reading:', :reading, ', reading time:', :reading_time));
                    insert into warnings_data.warnings(sensor_uuid, reason, reading, reading_time)
                    values(:uuid, :reason, :reading, :reading_time);
                end if;
                warning_reading_cursor_ts := reading_time;
            END FOR;
            truncate table warnings_data.warnings_reading_cursor;
            insert into warnings_data.warnings_reading_cursor (last_reading_ts) values (:warning_reading_cursor_ts);
            system$log_info('check_warnings() stored procedure ended');
        exception
            when other then
                system$log_error('check_warnings(): ' || sqlerrm);
        end;
    $$
    ;

    -- stored procedure to create a task that checks for warnings in reading table
    -- task creation must be deferred to after app install because
    -- it depends on a privilege being granted by the user via the UI
    create or replace procedure warnings_code.create_warning_check_task()
    returns varchar
    language sql
    as
    $$
        begin
            system$log_info('creating task warnings_data.check_warnings_every_minute...');
            create or replace task warnings_data.check_warnings_every_minute
              warehouse = reference('consumer_warnings_generation_warehouse')
              schedule = '1 minute'
            as
            call warnings_code.check_warnings();
        exception
            when other then
                system$log_error('create_warning_check_task(): ' || sqlerrm);
        end;
    $$
    ;

    -- stored procedure to resume or suspend check_warnings_every_minute task
    -- this stored procedure will be called from the UI
    create or replace procedure warnings_code.update_warning_check_task_status(enable boolean)
    returns varchar
    language sql
    as
    $$
        begin
            if (enable) then
                system$log_info('starting warning check task');
                alter task if exists warnings_data.check_warnings_every_minute resume;
                update config_data.configuration set enable_warning_generation_task = true;
            else
                system$log_info('stopping warning check task');
                alter task if exists warnings_data.check_warnings_every_minute suspend;
                update config_data.configuration set enable_warning_generation_task = false;
            end if;
        exception
            when other then
                system$log_error('update_warning_check_task_status(): ' || sqlerrm);
        end;
    $$
    ;
