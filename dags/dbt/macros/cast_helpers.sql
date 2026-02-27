{% macro safe_numeric(column_expression) -%}
{% set value_expression = "nullif(" ~ column_expression ~ ", '')" %}
case
    when {{ value_expression }} ~ '^-?[0-9]+(\.[0-9]+)?$' then {{ value_expression }}::numeric
    else null
end
{%- endmacro %}

{% macro safe_integer(column_expression) -%}
{% set value_expression = "nullif(" ~ column_expression ~ ", '')" %}
case
    when {{ value_expression }} ~ '^-?[0-9]+$' then {{ value_expression }}::integer
    else null
end
{%- endmacro %}

{% macro safe_boolean(column_expression) -%}
{% set value_expression = "nullif(" ~ column_expression ~ ", '')" %}
case
    when lower({{ value_expression }}) in ('true', 't', '1', 'yes', 'y') then true
    when lower({{ value_expression }}) in ('false', 'f', '0', 'no', 'n') then false
    else null
end
{%- endmacro %}
