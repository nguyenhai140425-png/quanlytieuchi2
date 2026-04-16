import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("master_admin", "0010_sync_eventcategory_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="parent_event",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="child_events",
                to="master_admin.event",
            ),
        ),
    ]
