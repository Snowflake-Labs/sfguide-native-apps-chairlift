-- This file is only used with Snowflake CLI (configured in snowflake.yml)
-- When creating the application package manually, create-package.sql will be used instead

-- For more information, refer to https://docs.snowflake.com/en/developer-guide/native-apps/preparing-data-content

-- mark that our application package depends on an external database in
-- the provider account. By granting "reference_usage", the proprietary data
-- in the chairlift_provider_data database can be shared through the app
grant reference_usage on database chairlift_provider_data
    to share in application package {{ package_name }};

-- now that we can reference our proprietary data, let's create some views
-- this "package schema" will be accessible inside of our setup script
create schema if not exists {{ package_name }}.package_shared;
use schema {{ package_name }}.package_shared;

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
  to share in application package {{ package_name }};
grant select on view package_shared.sensor_types_view
  to share in application package {{ package_name }};
grant select on view package_shared.sensor_ranges
  to share in application package {{ package_name }};
grant select on view package_shared.sensor_service_schedules
  to share in application package {{ package_name }};
