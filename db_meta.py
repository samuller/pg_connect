#
# We might consider constructing our queries with the PyPika in the future,
# but most of the main reasons it was considered are currently handled:
# - queries that aren't db-specific:
#   - not currently a priority
# - dynamically generating sql WHERE clauses to make filtering parameters optional:
#   - we use the following sql pattern "WHERE value is null or column = value"
# - escaping strings:
#  - done by psycopg2 when using parameters
# - avoiding sql injections:
#  - current use cases shouldn't require this
#  - using psycopg2 parameters does this for us
#  - Pypika doesn't seem to be able to use parameters and it's protection against sql injections is unknown
#
# from pypika import PostgreSQLQuery as Query, Table, Field


class TableColumn:

    def __init__(self, table_name, column_name, is_primary_key=None):
        self.table_name = table_name
        self.column_name = column_name
        self.is_primary_key = is_primary_key

    def __repr__(self):
        return "%s.%s%s" % (self.table_name, self.column_name, " *" if self.is_primary_key else "")


class ForeignKey:

    def __init__(self, name, table, columns, other_table, other_columns):
        self.name = name
        self.table = table
        self.columns = columns
        self.other_table = other_table
        self.other_columns = other_columns

    def __repr__(self):
        return "%s: %s.%s -> %s.%s" % (self.name, self.table, self.columns, self.other_table, self.other_columns)


def get_table_names(cursor, schema="public"):
    cursor.execute(sql_tables_in_db(), {'schema': schema})
    return [row[1] for row in cursor]


def get_column_names(cursor, table, schema="public"):
    sql = "SELECT * FROM %s.%s LIMIT 0" % (schema, table)
    cursor.execute(sql)
    return [row[0] for row in cursor.description]


def get_primary_key_column_names(cursor, table, schema="public"):
    cursor.execute(sql_primary_keys(), {'schema': schema, 'table': table})
    return [row[0] for row in cursor]


def get_columns(cursor, table, schema="public"):
    pk_columns = get_primary_key_column_names(cursor, table, schema)
    return [TableColumn(table, col, col in pk_columns) for col in get_column_names(cursor, table, schema)]


def get_foreign_keys(cursor, table=None, schema="public"):
    cursor.execute(sql_foreign_keys_of_table(), {'schema': schema, 'table': table})
    return [ForeignKey(row[2], row[0], [row[1]], row[3], [row[4]])
            for row in cursor]


def sql_tables_in_db():
    """Generate sql query to fetch all tables"""
    return """
    SELECT table_schema, table_name FROM information_schema.tables
    WHERE (%(schema)s is null OR table_schema = %(schema)s)
    ORDER BY table_schema, table_name;
    """


def sql_foreign_keys_of_table():
    """
    Does not work correctly for foreign key constraints that point
    to multiple columns
    """
    return """
    SELECT
        tc.table_name, kcu.column_name, tc.constraint_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM
        information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE constraint_type = 'FOREIGN KEY'
        AND (%(schema)s is null OR tc.table_schema = %(schema)s)
        AND (%(table)s is null OR tc.table_name = %(table)s)
    ORDER BY tc.constraint_name;"""


def psql_foreign_keys_of_table():
    """
    Postgres-specific is more accurate but harder to interpret as
    it gives constraint's definition in sql syntax.

    schema_table = schema + "." + table
    (schema_table, schema_table)
    """
    return """
    SELECT
        conname, pg_catalog.pg_get_constraintdef(r.oid, true) as condef
    FROM pg_catalog.pg_constraint r
    WHERE r.contype = 'f'
        AND (%s is null OR r.conrelid = %s::regclass)
    ORDER BY conname;"""


def sql_primary_keys():
    return """SELECT column_name
    FROM information_schema.table_constraints
    JOIN information_schema.key_column_usage
    USING(constraint_catalog, constraint_schema, constraint_name,
          table_catalog, table_schema, table_name)
    WHERE constraint_type = 'PRIMARY KEY'
        AND (%(schema)s is null OR table_schema = %(schema)s)
        AND (%(table)s is null OR table_name = %(table)s)
    ORDER BY ordinal_position;"""


def sql_column_default_values():
    return """SELECT column_name, column_default
    FROM information_schema.columns
    WHERE (%(schema)s is null OR table_schema = %(schema)s)
        AND (%(table)s is null OR table_name = %(table)s)
    ORDER BY ordinal_position;
    """
