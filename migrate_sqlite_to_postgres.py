import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import sys
import time


# ============================================================
# CONFIGURATION
# ============================================================

SQLITE_DB = "db.sqlite3"

PG_DB = "project3db"
PG_USER = "project3user"
PG_HOST = "127.0.0.1"
PG_PORT = 5432
PG_PASSWORD = "VMMCerp@2026"

BATCH_SIZE = 5000


# ============================================================
# SQLITE
# ============================================================

def get_sqlite_tables(sqlite_conn):
    rows = sqlite_conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()

    return [row[0] for row in rows]


def get_sqlite_columns(sqlite_conn, table):
    rows = sqlite_conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return [row[1] for row in rows]


# ============================================================
# POSTGRES
# ============================================================

def get_postgres_tables(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        return [row[0] for row in cur.fetchall()]


def get_postgres_columns(pg_conn, table):
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))

        return {
            row[0]: row[1]
            for row in cur.fetchall()
        }


# ============================================================
# QUOTING
# ============================================================

def quote_table(table):
    return '"' + table.replace('"', '""') + '"'


def quote_column(column):
    return '"' + column.replace('"', '""') + '"'


# ============================================================
# BOOLEAN CONVERSION
# ============================================================

def convert_value(value, postgres_type):
    """
    Convert SQLite values to values accepted by PostgreSQL.
    """

    if value is None:
        return None

    # SQLite stores Django BooleanField values as 0 / 1.
    if postgres_type == "boolean":

        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            return bool(value)

        if isinstance(value, str):
            value_lower = value.strip().lower()

            if value_lower in ("1", "true", "t", "yes", "y"):
                return True

            if value_lower in ("0", "false", "f", "no", "n"):
                return False

    return value


# ============================================================
# DEPENDENCY INFORMATION
# ============================================================

def get_postgres_dependencies(pg_conn):
    """
    Return:

        {
            child_table: {
                parent_table1,
                parent_table2
            }
        }
    """

    dependencies = {}

    with pg_conn.cursor() as cur:

        cur.execute("""
            SELECT
                tc.table_name AS child_table,
                ccu.table_name AS parent_table
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.constraint_column_usage AS ccu
              ON tc.constraint_name = ccu.constraint_name
             AND tc.table_schema = ccu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
        """)

        rows = cur.fetchall()

    for child, parent in rows:

        if child not in dependencies:
            dependencies[child] = set()

        if child != parent:
            dependencies[child].add(parent)

    return dependencies


# ============================================================
# DEPENDENCY ORDER
# ============================================================

def build_dependency_order(tables, dependencies):

    ordered = []
    remaining = set(tables)

    while remaining:

        progress = False

        for table in sorted(remaining):

            required = dependencies.get(table, set())

            # Only consider dependencies that are actually
            # present in the migration list.
            required = required.intersection(remaining)

            if not required:

                ordered.append(table)
                remaining.remove(table)
                progress = True
                break

        if not progress:

            print("\nWARNING:")
            print("Circular or unresolved dependency detected.")

            print("\nRemaining tables:")

            for table in sorted(remaining):
                print(
                    f"  {table} <- "
                    f"{', '.join(sorted(dependencies.get(table, set())))}"
                )

            print(
                "\nContinuing with remaining tables "
                "in alphabetical order."
            )

            ordered.extend(sorted(remaining))
            break

    return ordered


# ============================================================
# RESET SEQUENCES
# ============================================================

def reset_sequences(pg_conn):

    print("\nResetting PostgreSQL sequences...")

    with pg_conn.cursor() as cur:

        cur.execute("""
            SELECT
                table_name,
                column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_default LIKE 'nextval(%'
            ORDER BY table_name, ordinal_position
        """)

        sequences = cur.fetchall()

        for table, column in sequences:

            try:

                cur.execute(
                    """
                    SELECT pg_get_serial_sequence(%s, %s)
                    """,
                    (table, column)
                )

                sequence = cur.fetchone()[0]

                if not sequence:
                    continue

                cur.execute(
                    f"""
                    SELECT MAX({quote_column(column)})
                    FROM {quote_table(table)}
                    """
                )

                max_id = cur.fetchone()[0]

                if max_id is None:

                    cur.execute(
                        "SELECT setval(%s, 1, false)",
                        (sequence,)
                    )

                else:

                    cur.execute(
                        "SELECT setval(%s, %s, true)",
                        (sequence, max_id)
                    )

                print(
                    f"  {table}.{column} -> "
                    f"{max_id if max_id is not None else 1}"
                )

            except Exception as exc:

                print(
                    f"  WARNING: sequence reset failed for "
                    f"{table}.{column}: {exc}"
                )

                pg_conn.rollback()

    pg_conn.commit()


# ============================================================
# MIGRATION
# ============================================================

def main():

    print("=" * 70)
    print("SQLITE → POSTGRESQL MIGRATION")
    print("=" * 70)

    sqlite_conn = None
    pg_conn = None

    try:

        # ----------------------------------------------------
        # OPEN SQLITE
        # ----------------------------------------------------

        print("\nOpening SQLite database...")

        sqlite_conn = sqlite3.connect(SQLITE_DB)

        print("SQLite connection: OK")

        # ----------------------------------------------------
        # OPEN POSTGRES
        # ----------------------------------------------------

        print("\nOpening PostgreSQL database...")

        pg_conn = psycopg2.connect(
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD,
            host=PG_HOST,
            port=PG_PORT
        )

        print("PostgreSQL connection: OK")

        # ----------------------------------------------------
        # TABLE CHECK
        # ----------------------------------------------------

        sqlite_tables = get_sqlite_tables(sqlite_conn)
        postgres_tables = get_postgres_tables(pg_conn)

        print(
            f"\nSQLite tables:     {len(sqlite_tables)}"
        )

        print(
            f"PostgreSQL tables: {len(postgres_tables)}"
        )

        missing = [
            table
            for table in sqlite_tables
            if table not in postgres_tables
        ]

        if missing:

            print(
                "\nERROR: These SQLite tables "
                "do not exist in PostgreSQL:"
            )

            for table in missing:
                print("  ", table)

            sys.exit(1)

        print(
            "\nAll SQLite tables exist in PostgreSQL."
        )

        # ----------------------------------------------------
        # DEPENDENCIES
        # ----------------------------------------------------

        print(
            "\nReading PostgreSQL foreign-key dependencies..."
        )

        dependencies = get_postgres_dependencies(pg_conn)

        migration_order = build_dependency_order(
            sqlite_tables,
            dependencies
        )

        print("\nMigration order:")

        for index, table in enumerate(
            migration_order,
            start=1
        ):

            deps = dependencies.get(table, set())

            if deps:

                print(
                    f"  {index:02d}. {table} <- "
                    f"{', '.join(sorted(deps))}"
                )

            else:

                print(
                    f"  {index:02d}. {table}"
                )

        # ----------------------------------------------------
        # IMPORTANT
        # ----------------------------------------------------
        #
        # Do NOT use:
        #
        # SET session_replication_role = replica
        #
        # because project3user does not have permission.
        #
        # Instead we insert tables in dependency order.
        #

        print(
            "\nStarting data migration..."
        )

        print(
            "PostgreSQL constraints remain ENABLED."
        )

        print(
            "Tables will be inserted in dependency order."
        )

        total_rows = 0
        start_time = time.time()

        # ----------------------------------------------------
        # TABLE LOOP
        # ----------------------------------------------------

        for table_index, table in enumerate(
            migration_order,
            start=1
        ):

            sqlite_columns = get_sqlite_columns(
                sqlite_conn,
                table
            )

            postgres_columns = get_postgres_columns(
                pg_conn,
                table
            )

            # -----------------------------------------------
            # COMMON COLUMNS
            # -----------------------------------------------

            columns = [
                column
                for column in sqlite_columns
                if column in postgres_columns
            ]

            if not columns:

                print(
                    f"\n[{table_index}/{len(migration_order)}] "
                    f"{table}: NO COMMON COLUMNS - SKIPPED"
                )

                continue

            # -----------------------------------------------
            # ROW COUNT
            # -----------------------------------------------

            count = sqlite_conn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            print(
                f"\n[{table_index}/{len(migration_order)}] "
                f"{table}: {count:,} rows"
            )

            if count == 0:

                print(
                    "  Empty table - skipped"
                )

                continue

            # -----------------------------------------------
            # COLUMN SQL
            # -----------------------------------------------

            column_sql = ", ".join(
                quote_column(column)
                for column in columns
            )

            insert_sql = (
                f'INSERT INTO {quote_table(table)} '
                f'({column_sql}) VALUES %s'
            )

            select_sql = (
                f'SELECT {column_sql} '
                f'FROM {quote_table(table)}'
            )

            # -----------------------------------------------
            # SQLITE CURSOR
            # -----------------------------------------------

            sqlite_cursor = sqlite_conn.cursor()

            sqlite_cursor.execute(select_sql)

            inserted = 0

            # -----------------------------------------------
            # BATCH LOOP
            # -----------------------------------------------

            while True:

                rows = sqlite_cursor.fetchmany(
                    BATCH_SIZE
                )

                if not rows:
                    break

                # -------------------------------------------
                # CONVERT SQLITE → POSTGRES
                # -------------------------------------------

                converted_rows = []

                for row in rows:

                    converted_row = []

                    for index, value in enumerate(row):

                        column = columns[index]

                        postgres_type = postgres_columns[
                            column
                        ]

                        value = convert_value(
                            value,
                            postgres_type
                        )

                        converted_row.append(value)

                    converted_rows.append(
                        tuple(converted_row)
                    )

                # -------------------------------------------
                # INSERT
                # -------------------------------------------

                try:

                    with pg_conn.cursor() as cur:

                        execute_values(
                            cur,
                            insert_sql,
                            converted_rows,
                            page_size=BATCH_SIZE
                        )

                    pg_conn.commit()

                except Exception as exc:

                    pg_conn.rollback()

                    print(
                        "\n"
                        + "=" * 70
                    )

                    print(
                        f"ERROR inserting into table: {table}"
                    )

                    print(
                        "=" * 70
                    )

                    print(exc)

                    print(
                        "\nMigration stopped."
                    )

                    sqlite_cursor.close()

                    sys.exit(1)

                inserted += len(
                    converted_rows
                )

                total_rows += len(
                    converted_rows
                )

                # -------------------------------------------
                # PROGRESS
                # -------------------------------------------

                if count >= 10000:

                    percent = (
                        inserted / count
                    ) * 100

                    print(
                        f"\r  Progress: "
                        f"{inserted:,}/{count:,} "
                        f"({percent:.1f}%)",
                        end="",
                        flush=True
                    )

            sqlite_cursor.close()

            print(
                f"\n  Completed: {inserted:,} rows"
            )

        # ----------------------------------------------------
        # RESET SEQUENCES
        # ----------------------------------------------------

        reset_sequences(pg_conn)

        # ----------------------------------------------------
        # FINISHED
        # ----------------------------------------------------

        elapsed = time.time() - start_time

        print(
            "\n"
            + "=" * 70
        )

        print(
            "MIGRATION COMPLETED"
        )

        print(
            "=" * 70
        )

        print(
            f"Total rows transferred: "
            f"{total_rows:,}"
        )

        print(
            f"Time taken: "
            f"{elapsed / 60:.2f} minutes"
        )

    except KeyboardInterrupt:

        print(
            "\n\nMigration interrupted by user."
        )

        if pg_conn:
            pg_conn.rollback()

        sys.exit(1)

    except Exception as exc:

        print(
            "\n"
            + "=" * 70
        )

        print(
            "MIGRATION FAILED"
        )

        print(
            "=" * 70
        )

        print(exc)

        if pg_conn:
            pg_conn.rollback()

        sys.exit(1)

    finally:

        if sqlite_conn:
            sqlite_conn.close()

        if pg_conn:
            pg_conn.close()

        print(
            "\nDatabase connections closed."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
