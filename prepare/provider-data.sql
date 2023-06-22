use role chairlift_provider;
use warehouse chairlift_wh;

create database if not exists chairlift_provider_data;
use database chairlift_provider_data;
create schema if not exists core;
use schema core;

-- Sensor types with reading min range, max ranges, service intervals and lifetime of the sensor.
create or replace table chairlift_provider_data.core.sensor_types (
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

insert into chairlift_provider_data.core.sensor_types values
    (1, 'Brake Temperature', -40, 40, 6, 'month', 5, 'year'),
    (2, 'Current Load', 20000, 50000, 3, 'month', 5, 'year'),
    (3, 'Bull-wheel RPM', 4000, 5000, 1, 'month', 1, 'year'),
    (4, 'Motor RPM', 2000, 2500, 1, 'month', 1, 'year'),
    (5, 'Motor Voltage', 110, 130, 2, 'month', 5, 'year'),
    (6, 'Current Temperature', -40, 40, 4, 'month', 5, 'year'),
    (7, 'Rope Tension', 70, 100, 3, 'month', 5, 'year'),
    (8, 'Chairlift Load', 50, 250, 3, 'month', 2, 'year'),
    (9, 'Chairlift Vibration', 30, 100, 3, 'month', 3, 'year');
