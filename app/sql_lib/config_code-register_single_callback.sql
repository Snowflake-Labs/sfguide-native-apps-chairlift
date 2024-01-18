-- this callback is used by the UI to ultimately bind a reference that expects one value
create or replace procedure config_code.register_single_callback(ref_name string, operation string, ref_or_alias string)
returns string
language sql
as $$
    begin
        case (operation)
            when 'ADD' then
                select system$set_reference(:ref_name, :ref_or_alias);
            when 'REMOVE' then
                select system$remove_reference(:ref_name);
            when 'CLEAR' then
                select system$remove_reference(:ref_name);
            else
                return 'Unknown operation: ' || operation;
        end case;
        system$log('debug', 'register_single_callback: ' || operation || ' succeeded');
        return 'Operation ' || operation || ' succeeded';
    end;
$$;

grant usage on procedure config_code.register_single_callback(string, string, string)
    to application role app_admin;
