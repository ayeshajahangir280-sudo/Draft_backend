from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("draft", "0002_category")]
    operations = [migrations.CreateModel(
        name="DraftPlayer",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("draft", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="draft_players", to="draft.draft")),
            ("player", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="draft_entries", to="draft.player")),
        ],
        options={"constraints": [models.UniqueConstraint(fields=("draft", "player"), name="unique_player_per_draft_pool")]},
    )]
