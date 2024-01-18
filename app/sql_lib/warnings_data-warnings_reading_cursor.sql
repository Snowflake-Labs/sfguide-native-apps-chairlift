--This table keep track of what was the last reading that was processed for warnings.
create table if not exists warnings_data.warnings_reading_cursor (
    last_reading_ts timestamp not null
);

grant select on table warnings_data.warnings_reading_cursor to application role app_admin;
