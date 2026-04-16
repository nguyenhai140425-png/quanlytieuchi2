from django.db import migrations


def sync_eventcategory_table(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    if "master_admin_eventcategory" not in existing_tables:
        schema_editor.execute(
            """
            CREATE TABLE master_admin_eventcategory (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                quantity INTEGER NOT NULL DEFAULT 1,
                event_id BIGINT NOT NULL REFERENCES master_admin_event (id) DEFERRABLE INITIALLY DEFERRED,
                category_id BIGINT NOT NULL REFERENCES master_admin_category (id) DEFERRABLE INITIALLY DEFERRED
            )
            """
        )
        schema_editor.execute(
            "CREATE INDEX master_admin_eventcategory_event_id_1405339d ON master_admin_eventcategory (event_id)"
        )
        schema_editor.execute(
            "CREATE INDEX master_admin_eventcategory_category_id_296ac230 ON master_admin_eventcategory (category_id)"
        )

    if "master_admin_event_categories" in existing_tables:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO master_admin_eventcategory (event_id, category_id, quantity)
            SELECT old.event_id, old.category_id, 1
            FROM master_admin_event_categories AS old
            WHERE NOT EXISTS (
                SELECT 1
                FROM master_admin_eventcategory AS new
                WHERE new.event_id = old.event_id AND new.category_id = old.category_id
            )
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ("master_admin", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sync_eventcategory_table, migrations.RunPython.noop),
    ]
