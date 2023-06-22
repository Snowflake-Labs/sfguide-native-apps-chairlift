use role chairlift_provider;
use warehouse chairlift_wh;

-- create our application package
-- at this point, the package will not be installable because
-- it does not have a version; the version will be uploaded later
create application package if not exists chairlift_pkg;

-- mark that our application package depends on an external database in
-- the provider account. By granting "reference_usage", the proprietary data
-- in the chairlift_provider_data database can be shared through the app
grant reference_usage on database chairlift_provider_data
    to share in application package chairlift_pkg;

-- now that we can reference our proprietary data, let's create some views
-- this "package schema" will be accessible inside of our setup script
create schema if not exists chairlift_pkg.package_shared;
use schema chairlift_pkg.package_shared;

-- View for sensor types full data
create view if not exists package_shared.sensor_types_view
  as select id, name, min_range, max_range, service_interval_count, service_interval_unit, lifetime_count, lifetime_unit
  from chairlift_provider_data.core.sensor_types;

-- View for sensor reading ranges
create view if not exists package_shared.sensor_ranges
  as select id, min_range, max_range
  from chairlift_provider_data.core.sensor_types;

-- View for sensor service scheduling
create view if not exists package_shared.sensor_service_schedules
  as select
    id,
    service_interval_count,
    service_interval_unit,
    lifetime_count,
    lifetime_unit
  from chairlift_provider_data.core.sensor_types;

-- these grants allow our setup script to actually refer to our views
grant usage on schema package_shared
  to share in application package chairlift_pkg;
grant select on view package_shared.sensor_types_view
  to share in application package chairlift_pkg;
grant select on view package_shared.sensor_ranges
  to share in application package chairlift_pkg;
grant select on view package_shared.sensor_service_schedules
  to share in application package chairlift_pkg;
