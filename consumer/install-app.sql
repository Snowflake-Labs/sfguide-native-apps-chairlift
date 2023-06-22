use role chairlift_admin;
use warehouse chairlift_wh;

-- create the actual application from the package in versioned dev mode
create application chairlift_app
    from application package chairlift_pkg
    using version develop;

-- allow our secondary viewer role restricted access to the app
grant application role chairlift_app.app_viewer
    to role chairlift_viewer;
