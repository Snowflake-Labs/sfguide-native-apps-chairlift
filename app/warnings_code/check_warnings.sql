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
