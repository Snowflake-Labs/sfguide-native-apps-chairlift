-- View for sensor reading ranges
create or replace view shared_content.sensor_ranges
    as select * from package_shared.sensor_ranges;
