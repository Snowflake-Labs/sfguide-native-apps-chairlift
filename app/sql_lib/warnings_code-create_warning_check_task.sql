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
