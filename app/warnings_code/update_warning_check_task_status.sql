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
