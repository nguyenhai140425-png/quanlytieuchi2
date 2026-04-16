from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("master_admin", "0011_event_parent_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="child_event_target_count",
            field=models.IntegerField(default=0),
        ),
    ]
