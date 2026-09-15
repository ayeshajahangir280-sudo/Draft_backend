from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("draft", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=32, unique=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
    ]
