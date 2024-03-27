# Chairlift sample app

This Snowflake Native Application sample demonstrates how a ChairLift manufacture can use native apps to share data with their consumers, analyze equipment data collected on the consumer side, and generate warnings based on such analysis.

## Directory structure

- `prepare/`: scripts to prepare the development and test accounts (roles, data)
- `provider/`: script to create the application package with appropriate grants
- `consumer/`: script to install the application as the consumer
- `app/`: application entry point and source files

## Getting started

In many production use cases, there are two account types involved in the deployment of an application: the _provider_ account, which is responsible for creating the application package and listing it on the Snowflake Marketplace, and _consumer_ accounts, which are defined as any accounts that have installed the app. For the purposes of this sample, we will instead focus on same-account deployment: one account is used as both the provider _and_ consumer.

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

## Use Snow CLI for creating and installing the application (recommended)

**Note**: Snowflake CLI is in Private Preview (PrPr). For more information on enrollment in the Snowflake CLI PrPr program or to obtain the relevant documentation, please contact a Snowflake sales representative.

### Create application package and install application
Once Snowflake CLI is installed and configured, run the following command in your terminal from this project's root directory:
```
snow app run
```

This command will upload source files and create the application package and install the application instance automatically. 

Snowflake CLI project is configured using `snowflake.yml` file.

## Alternatively, you can manually create and install the application

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

## Consumer workflow
### Consumer: Run application as chairlift_admin (snowsight)

Earlier, you created two roles that have differing levels of access to the application you have just installed:

- `chairlift_admin` allows you to configure the application as well as dismiss warnings and view sensor data, while
- `chairlift_viewer` is a restricted role that only allows viewing sensor data, and does not have access to the `Configuration` tab.

Visit the Snowflake UI, and switch to the `chairlift_admin` role. Locate the `Apps` tab in the account, then select the `chairlift_app`.

### Consumer: First-time setup

This example includes a "walkthrough" that will guide you through granting privileges and binding references that the app needs to function. The following table describes the purpose of each reference, and how to select the appropriate object within your Snowflake account to allow the application to function properly.

|Reference|Purpose|Action|
|-----|----|----|
|Consumer warning check warehouse|Defines where the application task should run|Choose a warehouse that your current role (i.e. `chairlift_admin`) has access to|
|Chairlift machines|A record of all chairlifts at your fictional resort|Choose `chairlift_consumer_data.data.machines`|
|Chairlift sensors|A record of all sensors configured on these machines|Choose `chairlift_consumer_data.data.sensors`|
|Chairlift sensor readings|Data recorded from the above sensors, generated by `chairlift_consumer.data.populate_reading`|Choose `chairlift_consumer_data.data.sensor_readings`|

Because the privilege has been declared in the application manifest, consumers can grant `EXECUTE TASK` to the application by clicking the `Request Privileges` button when it comes up.

After you have completed all of the steps, you can click "Continue to app" to proceed. Once you have done so, navigate to the "Configuration" tab in order to generate warnings based on the sensor data you created earlier by running the contents of `prepare/consumer-data.sql`.

#### Application tabs

- **Configuration** allows the `chairlift_admin` to generate warnings based on sensor readings that are outside of the normal operating range.
- **Dashboard** allows the `chairlift_admin` to see the warnings generated and dismiss them.
- **Sensor data** shows a graphical overview of data that has recently been generated by `populate_reading` and allows some rudimentary filtering as well as visualization of the normal operating range of each statistic.

### Consumer: Run as chairlift_viewer

You can switch to the `chairlift_viewer` role by exiting out of the application, switching your role at the top-left of the Snowflake UI, then navigating back to `chairlift_app` in the `Apps` tab.

### Consumer: Cleaning up

In order to ensure this example is not consuming any credits in your account, we suggest disabling warning generation (using the Configuration tab in the UI) and the sensor reading generation task (if resumed) by executing the following as `chairlift_admin`:

```sql
alter task chairlift_consumer_data.data.populate_reading_every_minute suspend;
```

The application itself can be uninstalled by calling:
```
snow app teardown
```
or

```sql
drop application chairlift_app;
```

#### Additional resources

- [Snowflake Native App Developer Toolkit](https://www.snowflake.com/snowflake-native-app-developer-toolkit/?utm_source=github&utm_medium=github&utm_campaign=na-us-en-eb-developer-toolkit-github)

