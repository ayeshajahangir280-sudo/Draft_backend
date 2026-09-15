from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from draft.models import Draft, DraftTeam, Player, Team, UserProfile, UserRole


TEAMS = [
    ("Falcon Warriors", "FW"),
    ("Yuva Force", "YF"),
    ("Shuttle Shots", "SS"),
    ("Asfar Amigos", "AA"),
    ("Golden Axis Mavericks", "GAM"),
    ("Team Six", "T6"),
    ("Team Seven", "T7"),
    ("Team Eight", "T8"),
]

PLAYERS = [
    ("Ahmed Khan", "A", "All-Rounder"),
    ("Bilal Ahmed", "A", "Batsman"),
    ("Usman Ali", "A", "Bowler"),
    ("Hassan Raza", "A", "Wicket Keeper"),
    ("Zain Abbas", "A", "Batsman"),
    ("Faisal Iqbal", "A", "Bowler"),
    ("Imran Shah", "B", "All-Rounder"),
    ("Kamran Yousuf", "B", "Batsman"),
    ("Rizwan Malik", "B", "Wicket Keeper"),
    ("Tariq Mehmood", "B", "Bowler"),
    ("Adeel Nawaz", "B", "Batsman"),
    ("Shoaib Anwar", "B", "All-Rounder"),
    ("Junaid Aslam", "C", "Bowler"),
    ("Waqas Haider", "C", "Batsman"),
    ("Noman Sheikh", "C", "All-Rounder"),
    ("Saad Qureshi", "C", "Wicket Keeper"),
    ("Danish Farooq", "C", "Bowler"),
    ("Hamza Tariq", "C", "Batsman"),
    ("Owais Siddiqui", "D", "All-Rounder"),
    ("Rehan Butt", "D", "Bowler"),
    ("Talha Javed", "D", "Batsman"),
    ("Yasir Kamal", "D", "Wicket Keeper"),
    ("Arsalan Ejaz", "D", "Batsman"),
    ("Moiz Hussain", "D", "Bowler"),
]


class Command(BaseCommand):
    help = "Seed demo draft data matching the existing frontend."

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True})
        admin.set_password("admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        UserProfile.objects.update_or_create(user=admin, defaults={"role": UserRole.ADMIN})

        draft, _ = Draft.objects.get_or_create(name="Stride Player Draft", defaults={"active_category": "A"})
        for i, (name, short) in enumerate(TEAMS, start=1):
            manager, _ = User.objects.get_or_create(username=f"manager{i}")
            manager.set_password("manager123")
            manager.save()
            UserProfile.objects.update_or_create(user=manager, defaults={"role": UserRole.MANAGER})
            team, _ = Team.objects.update_or_create(
                name=name,
                defaults={"short": short, "manager": manager},
            )
            DraftTeam.objects.get_or_create(draft=draft, team=team, manager=manager)

        for i, (name, category, role) in enumerate(PLAYERS, start=1):
            Player.objects.update_or_create(
                name=name,
                defaults={
                    "category": category,
                    "playing_role": role,
                    "photo": f"https://i.pravatar.cc/400?img={(i % 60) + 11}",
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded demo users, teams, players, and draft."))
