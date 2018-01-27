#!/usr/bin/env python3
import os
import click
from sqlalchemy import create_engine, inspect

found_config = True
try:
    import config as cfg
except ImportError:
    found_config = False


def export_all(engine, inspector, schema, output_dir, file_format="CSV HEADER"):
    conn = engine.raw_connection()
    try:
        cursor = conn.cursor()

        tables = sorted(inspector.get_table_names(schema))
        for table in tables:
            output_file = open(os.path.join(output_dir, table + '.csv'), 'wb')
            copy_sql = 'COPY %s TO STDOUT WITH %s' % (table, file_format)
            cursor.copy_expert(copy_sql, output_file)

        conn.commit()
    finally:
        conn.close()


def get_unique_columns(inspector, table, schema):
    pks = inspector.get_primary_keys(table, schema)
    unique_constraints = inspector.get_unique_constraints(table, schema)
    unique = [col for constraint in unique_constraints for col in constraint['column_names']]
    return pks + unique


def sql_delete_identical_tmp_data(table_name, temp_table_name, all_column_names):
    # "IS NOT DISTINCT FROM" handles NULLS better (even composite type columns), but is not indexed
    # where_clause = " AND ".join(["%s.%s IS NOT DISTINCT FROM %s.%s" % (table, col, temp_table_name, col)
    #                               for col in all_columns])
    where_clause = " AND ".join(["(%s.%s = %s.%s OR (%s.%s IS NULL AND %s.%s IS NULL))"
                                 % (table_name, col, temp_table_name, col, table_name, col, temp_table_name, col)
                                 for col in all_column_names])
    delete_sql = "DELETE FROM %s USING %s WHERE %s;" % \
                 (temp_table_name, table_name, where_clause)
    return delete_sql


def import_all_new(engine, inspector, schema, input_dir, file_format="CSV HEADER"):
    """
    Imports files that introduce new or updated rows. These files have the exact structure
    of the final desired table except that they might be missing rows.
    """
    conn = engine.raw_connection()
    try:
        cursor = conn.cursor()
        # assert conn.server_version >= 90500, \
        #     'Postgresql 9.5 or later required for INSERT ... ON CONFLICT: %s' % (conn.server_version,)

        tables = sorted(inspector.get_table_names(schema))
        total_stats = {'skip': 0, 'insert': 0, 'update': 0}
        # For now we assume a file for each table
        for table in tables:
            id_columns = get_unique_columns(inspector, table, schema)
            if len(id_columns) == 0:
                print("Skipping table '%s' as it has no primary key or unique columns!" % (table,))
                continue
            all_columns = [col['name'] for col in inspector.get_columns(table, schema)]
            stats = {'skip': 0 ,'insert': 0, 'update': 0}

            temp_table_name = "_tmp_%s" % (table,)
            input_file = open(os.path.join(input_dir, table + '.csv'), 'r')
            # Create temporary table with same columns and types as target table
            create_sql = "CREATE TEMP TABLE %s AS SELECT * FROM %s LIMIT 0;" % (temp_table_name, table)
            cursor.execute(create_sql)
            # Import data into temporary table
            copy_sql = 'COPY %s FROM STDOUT WITH %s' % (temp_table_name, file_format)
            cursor.copy_expert(copy_sql, input_file)

            # Delete data that is already identical to that in destination table
            cursor.execute(sql_delete_identical_tmp_data(table, temp_table_name, all_columns))
            stats['skip'] = cursor.rowcount

            # insert_sql = "INSERT INTO %s SELECT * FROM %s WHERE 1 = 1;" % (table, temp_table_name)
            # cursor.execute(insert_sql)

            # UPDATE table_b SET column1 = a.column1, column2 = a.column2, column3 = a.column3
            # FROM table_a WHERE table_a.id = table_b.id AND table_b.id in (1, 2, 3)
            set_columns = ",".join(["%s = %s.%s" % (col, temp_table_name, col)
                                    for col in all_columns])
            match_columns = " AND ".join(["%s.%s = %s.%s" % (table, col, temp_table_name, col)
                                          for col in id_columns])
            update_sql = "UPDATE %s SET %s FROM %s WHERE %s" % (table, set_columns, temp_table_name, match_columns)
            cursor.execute(update_sql)
            stats['update'] = cursor.rowcount

            drop_sql = "DROP TABLE %s" % (temp_table_name,)
            cursor.execute(drop_sql)

            print("%s:\n\t skip: %s \t insert: %s \t update: %s" %
                  (table, stats['skip'], stats['insert'], stats['update'] ))
            total_stats = {k: total_stats.get(k, 0) + stats.get(k, 0) for k in set(total_stats) | set(stats)}

        print()
        print("Total results:\n\t skip: %s \n\t insert: %s \n\t update: %s" %
              (total_stats['skip'], total_stats['insert'], total_stats['update']))

        conn.commit()
    finally:
        conn.close()


@click.command(context_settings=dict(max_content_width=120))
@click.option('--dbname', '-d', help='database name to connect to', required=True)
@click.option('--host', '-h', help='database server host or socket directory (default: localhost)', default='localhost')
@click.option('--port', '-p', help='database server port (default: 5432)', default='5432')
@click.option('--username', '-U', help='database user name', default=lambda: os.environ.get('USER', 'postgres'))
@click.option('--schema', '-s', default="public", help='database schema to use (default: public)')
@click.option('--password', '-W', hide_input=True, prompt=not found_config,
              default=cfg.DB_PASSWORD if found_config else None,
              help='database password (default is to prompt for password or read config)')
@click.option('--export', '-e', is_flag=True, help='export all tables to directory')
@click.option('--config', '-c', help='config file')
@click.argument('directory', default='tmp')
@click.version_option(version='0.0.1')
def main(dbname, host, port, username, password, schema,
         config, export, directory):

    url = "postgresql://%s:%s@%s:%s/%s" % (username, password, host, port, dbname)
    engine = create_engine(url)
    inspector = inspect(engine)
    if schema is None:
        schema = inspector.default_schema_name
        # print(inspector.get_schema_names())

    if export:
        export_all(engine, inspector, schema, directory)
    else:
        print("TODO: implement import")
        # import_all(engine, inspector, schema, directory)


if __name__ == "__main__":
    main()