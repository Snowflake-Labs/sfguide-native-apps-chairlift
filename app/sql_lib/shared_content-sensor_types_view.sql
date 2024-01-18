-- View for sensor types full data
create or replace view shared_content.sensor_types_view
    as select * from package_shared.sensor_types_view;
