-- This is the setup script that will run while installing your application instance in a consumer's account.
-- For more information on how to create setup file, visit https://docs.snowflake.com/en/developer-guide/native-apps/creating-setup-script

-- this app exposes 2 application roles: admin and viewer
create application role if not exists app_admin;
create application role if not exists app_viewer;

-- viewer permissions are a subset of those for the admin
grant application role app_viewer to application role app_admin;

-- the config data schema holds configuration data
-- we create a non-versioned schema "if not exists"
-- so that we do not clobber state whenever we upgrade the app
create schema if not exists config_data;
    grant usage on schema config_data to application role app_admin;
    execute immediate from './config_data/configuration.sql';

-- non-versioned schema to prevent data loss on upgrade
-- we'll also store our task(s) here
create schema if not exists warnings_data;
    grant usage on schema warnings_data to application role app_admin;
    execute immediate from './warnings_data/warnings_reading_cursor.sql';
    execute immediate from './warnings_data/warnings.sql';

-- the ui schema holds all streamlits
create or alter versioned schema ui;
    grant usage on schema ui to application role app_viewer;
    execute immediate from './ui/v_dashboard.sql';
    execute immediate from './ui/v_sensor_data.sql';
    execute immediate from './ui/v_configuration.sql';

-- simple generic methods to register callbacks
create or alter versioned schema config_code;
    grant usage on schema config_code to application role app_admin;
    execute immediate from './config_code/register_single_callback.sql';

-- we need two views for each table we want to share from the provider through the app:
-- one set of views live in the package schema; the other set of views are defined here
create or alter versioned schema shared_content;
    execute immediate from './shared_content/sensor_types_view.sql';
    execute immediate from './shared_content/sensor_ranges.sql';
    execute immediate from './shared_content/sensor_service_schedules.sql';

-- versioned schema to hold our stored procedures
create or alter versioned schema warnings_code;
    execute immediate from './warnings_code/check_warnings.sql';
    execute immediate from './warnings_code/create_warning_check_task.sql';
    execute immediate from './warnings_code/update_warning_check_task_status.sql';
