use role chairlift_admin;
use warehouse chairlift_wh;

-- consumer data: streaming readings from sensors on their ski lift machines.
create database if not exists chairlift_consumer_data;
use database chairlift_consumer_data;
create schema if not exists data;
use schema data;

-- what machines (chairlifts and stations) exist in the consumer's ski resort?
create or replace table machines (
    uuid varchar,
    name varchar,
    latitude double,
    longitude double,
    primary key (uuid)
);

-- what sensors are configured and streaming data from those machines?
create or replace table sensors (
    uuid varchar,
    name varchar,
    sensor_type_id int,
    machine_uuid varchar,
    last_reading int,
    installation_date date,
    last_service_date date,
    primary key (uuid),
    foreign key (machine_uuid) references machines(uuid)
);

-- what readings have we received from the configured sensors?
create table if not exists sensor_readings (
    sensor_uuid varchar,
    reading_time timestamp,
    reading int,
    primary key (sensor_uuid, reading_time),
    foreign key (sensor_uuid) references sensors(uuid)
);

-- Sensor types with reading min range, max ranges, service intervals and lifetime of the sensor.
-- Note that both the consumer and provider have a version of this table; you can think
-- of this version as coming from an imaginary "second app" which is a connector that
-- streams data into the consumer's account from the sensors. Consumer owns their own data!
create or replace table sensor_types (
    id int,
    name varchar,
    min_range int,
    max_range int,
    service_interval_count int,
    service_interval_unit varchar,
    lifetime_count int,
    lifetime_unit varchar,
    primary key (id)
);

insert into sensor_types values
    (1, 'Brake Temperature', -40, 40, 6, 'month', 5, 'year'),
    (2, 'Current Load', 20000, 50000, 3, 'month', 5, 'year'),
    (3, 'Bull-wheel RPM', 4000, 5000, 1, 'month', 1, 'year'),
    (4, 'Motor RPM', 2000, 2500, 1, 'month', 1, 'year'),
    (5, 'Motor Voltage', 110, 130, 2, 'month', 5, 'year'),
    (6, 'Current Temperature', -40, 40, 4, 'month', 5, 'year'),
    (7, 'Rope Tension', 70, 100, 3, 'month', 5, 'year'),
    (8, 'Chairlift Load', 50, 250, 3, 'month', 2, 'year'),
    (9, 'Chairlift Vibration', 30, 100, 3, 'month', 3, 'year');

-- what is the most-recent reading we have from a given sensor?
create view if not exists last_readings as
    select uuid, name, last_reading from sensors;

-- mock data in machines
insert into machines(uuid, name) select uuid_string(), 'Base Station';
insert into machines(uuid, name) select uuid_string(), 'Hilltop Station';
insert into machines(uuid, name) select uuid_string(), 'Chairlift #1';
insert into machines(uuid, name) select uuid_string(), 'Chairlift #2';
insert into machines(uuid, name) select uuid_string(), 'Chairlift #3';

-- mock data in sensors
execute immediate $$
declare
    c1 cursor for
        select uuid from machines where name = 'Base Station' or name = 'Hilltop Station';
    c2 cursor for
        select uuid from machines where name in ('Chairlift #1', 'Chairlift #2', 'Chairlift #3');
begin
    --for base and hilltop stations/machines
    for machine in c1 do
        let machine_uuid varchar default machine.uuid;
        insert into sensors(uuid, name, sensor_type_id, machine_uuid, installation_date, last_service_date)
            select uuid_string(), name, id, :machine_uuid, dateadd(day, -365, getdate()), dateadd(day, -1 * abs(hash(uuid_string()) % 365), getdate())
                from sensor_types where id < 8;
    end for;
    --for chairlifts machines
    for machine in c2 DO
        let machine_uuid varchar default machine.uuid;
        insert into sensors(uuid, name, sensor_type_id, machine_uuid, installation_date,last_service_date)
            select uuid_string(), name, id, :machine_uuid, dateadd(day, -365, getdate()), dateadd(day, -1 * abs(hash(uuid_string()) % 365), getdate())
                from sensor_types where id > 7;
    end for;
end;
$$
;

-- mock data in sensor_readings table
create or replace procedure populate_reading()
  returns varchar
  language sql
  as
  $$
    declare
      starting_ts       timestamp;
      rows_to_produce   integer;
      sensors_cursor cursor for
        select id, uuid, min_range, max_range
          from sensors s join sensor_types sr
                 on s.sensor_type_id = sr.id;
    begin
      --
      -- starting_ts is the time of the last sensor reading we wrong or, if no
      -- readings are available, 10 minutes in the past.
      --
      select coalesce(max(reading_time), dateadd(second, -30*20, current_timestamp()))
               into :starting_ts
        from sensor_readings;

      --
      -- produce one row for every thirty seconds from our starting time to now
      --
      rows_to_produce := datediff(second, starting_ts, current_timestamp()) / 30;

      for sensor in sensors_cursor do
        let sensor_uuid varchar default sensor.uuid;
        let min_range integer default sensor.min_range;
        let max_range integer default sensor.max_range;
  
        insert into sensor_readings(sensor_uuid, reading_time, reading)
          select
              :sensor_uuid,
              dateadd(second, row_id * 30, :starting_ts),
              case
                when rand_value < 10 then
                  :min_range - abs(hash(uuid)) % 10
                when rand_value > 90 then
                  :max_range + abs(hash(uuid)) % 10
                else
                  :min_range + abs(hash(uuid)) % (:max_range - :min_range)
              end case
          from ( 
              select seq4() + 1            as row_id,
                     uuid_string()         as uuid,
                     abs(hash(uuid)) % 100 as rand_value
                from table(generator(rowcount => :rows_to_produce)));
      end for;

      update sensors
         set last_reading = r.reading
        from sensors as s2, sensor_readings as r
       where s2.uuid = sensors.uuid
         and r.sensor_uuid = s2.uuid
         and r.reading_time = 
              (select max(reading_time)  
                 from sensor_readings r2
                where r2.sensor_uuid = s2.uuid);
    end;
  $$
;

-- Task to call the stored procedure to update the readings table every minute
create or replace task populate_reading_every_minute
    warehouse = chairlift_wh
    schedule = '1 minute'
as
    call populate_reading();

-- If you want the data to be populated on a schedule, you can run:
-- alter task chairlift_consumer_data.data.populate_reading_every_minute resume;

-- To stop the task:
-- alter task chairlift_consumer_data.data.populate_reading_every_minute suspend;

-- Get some initial data in the readings table
call populate_reading();
