create table if not exists warnings_data.warnings (
    sensor_uuid varchar,
    reading int,
    reading_time timestamp,
    reason varchar,
    acknowledged boolean default false,
    created_at timestamp default current_timestamp()
);

grant select on table warnings_data.warnings to application role app_admin;
