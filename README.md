# Chairlift sample app

This Snowflake Native Application sample demonstrates how a ChairLift manufacture can use native apps to share data with their consumers, analyze equipment data collected on the consumer side, and generate warnings based on such analysis.

## Directory structure

- `prepare/`: scripts to prepare the development and test account (roles, data)
- `provider/`: script to create the application package with appropriate grants
- `consumer/`: script to install the application as the consumer
- `src/`: source files for the application

## Getting started with same account development

### Set up account roles

To setup the development environment, some roles need to be configured first. This only needs to be done once.

#### Provider role and permissions

Execute `prepare/provider-role.sql` as the `accountadmin` role. This creates a role with appropriate permissions to create the application package.

#### Consumer roles and permissions

Execute `prepare/consumer-roles.sql` as the `accountadmin` role. This creates 2 roles, both of which will have access to the installed application, but with different permissions.

### Prepare objects in account

To mimic the production environment, some databases, schemas, tables etc. need to be setup, representing existing objects in the provider and consumer accounts. This only needs to be done once.

#### Provider data

Execute `prepare/provider-data.sql` as the `chairlift_provider` role. This script sets up the `sensor_type` table, which will be used by the application.

#### Consumer data

Execute `prepare/consumer-data.sql` as the `chairlift_admin` role. This script sets up tables for machines, sensors, and their readings.

### Create application package

#### Provider creates package

Execute `provider/create-package.sql` as the `chairlift_provider` role. This creates the `chairlift_pkg` application package, and grants it privileges on the provider data.

#### Upload source files to a stage

Files can be uploaded through the Snowflake UI, using the SnowSQL command line tool, or the Snowflake VSCode extension. The rest of this guide assumes that files are uploaded to the stage `@chairlift_pkg.code.source` which lives inside of the `code` schema of the application package database.

Before uploading the code, the schema and stage object must be created:
```SQL
create schema if not exists chairlift_pkg.code;
create stage if not exists chairlift_pkg.code.source;
```

#### Create new version or patch

Source code needs to be added to the application package as a new version:
```SQL
alter application package chairlift_pkg add version develop using '@chairlift_pkg.code.source';
```

Alternatively (except for the first time), source can be added as a new patch:
```SQL
alter application package chairlift_pkg add patch for version develop using '@chairlift_pkg.code.source';
```
This command returns the new patch number, which will be used to install the application as the consumer.

### Consumer installs application

To test installing the application in the same account, the provider role needs to grant the following to the consumer role (execute as `chairlift_provider`):
```SQL
grant install, develop on application package chairlift_pkg to role chairlift_admin;
```

Execute `consumer/install-app.sql` as the `chairlift_admin` role. This installs the application in the account, and grants appropriate privileges to the `chairlift_viewer` role.

Note that the version and/or patch values may need to be updated to install the application using a different version or patch.

### Consumer: Run application (snowsight)

Visit the Snowflake UI and locate the `Apps` tab in the account, select the `chairlift_app`.

Switch between `chairlift_admin` and `chairlift_viewer` roles by exiting out of the application, switching your role at the top-left of the Snowflake UI, and navigating back to `chairlift_app` in the `Apps` tab. These account roles have visibility to different UI tabs. In particular, the `chairlift_viewer` role does not have access to the `Configuration` tab.
