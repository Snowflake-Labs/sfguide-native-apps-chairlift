-- View for sensor service scheduling
create or replace view shared_content.sensor_service_schedules
    as select * from package_shared.sensor_service_schedules;
