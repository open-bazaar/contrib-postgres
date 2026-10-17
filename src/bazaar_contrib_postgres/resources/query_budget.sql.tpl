SELECT set_config('statement_timeout', {{ bind(milliseconds | string) }}, true)
