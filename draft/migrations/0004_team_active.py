from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("draft", "0003_draftplayer")]
    operations = [migrations.AddField(
        model_name="team",
        name="is_active",
        field=models.BooleanField(db_index=True, default=True),
    )]
