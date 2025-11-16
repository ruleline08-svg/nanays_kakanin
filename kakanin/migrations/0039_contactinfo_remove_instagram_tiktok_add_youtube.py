from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kakanin", "0038_product"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="contactinfo",
            name="instagram",
        ),
        migrations.RemoveField(
            model_name="contactinfo",
            name="tiktok",
        ),
        migrations.AddField(
            model_name="contactinfo",
            name="youtube",
            field=models.URLField(blank=True),
        ),
    ]
