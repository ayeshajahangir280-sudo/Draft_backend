from django.db import migrations, models
import django.db.models.deletion


def link_existing_categories(apps, schema_editor):
    Player = apps.get_model("draft", "Player")
    Category = apps.get_model("draft", "Category")
    for player in Player.objects.all().iterator():
        category, _ = Category.objects.get_or_create(name=player.category)
        player.category_ref_id = category.id
        player.save(update_fields=["category_ref"])


class Migration(migrations.Migration):
    dependencies = [("draft", "0004_team_active")]
    operations = [
        migrations.AddField(
            model_name="player",
            name="category_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="players",
                to="draft.category",
            ),
        ),
        migrations.RunPython(link_existing_categories, migrations.RunPython.noop),
    ]
