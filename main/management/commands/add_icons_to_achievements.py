from django.core.management.base import BaseCommand
from main.models import Achievement


class Command(BaseCommand):
    help = 'Добавляет иконки из Imgur к достижениям'

    def handle(self, *args, **options):
        icons = {
            'Беренче адым': 'https://i.imgur.com/XohRe4a.png',
            'Тырыш укучы': 'https://i.imgur.com/TIof7mx.png',
            'Идеаль тәртип': 'https://i.imgur.com/JH396An.png',
            'Сүз остасы': 'https://i.imgur.com/GecHVPf.png',
            'Математик батыр': 'https://i.imgur.com/I9Iegaw.png',
            'Тарих сөюче': 'https://i.imgur.com/YiqIJXi.png',
            'Мәргән': 'https://i.imgur.com/UNjYnrd.png',
            'Алтын каләм': 'https://i.imgur.com/7HckzBJ.png',
            'Белем энҗесе': 'https://i.imgur.com/6pikUYv.png',
            'Алтын тырышлык': 'https://i.imgur.com/kMoG0nO.png',
            'Төнге өкө': 'https://i.imgur.com/rMm56YO.png',
            'Иртә кошы': 'https://i.imgur.com/kOdr04h.png',
            'Яшен тизлеге': 'https://i.imgur.com/JcpbVOv.png',
            'Дуслык көче': 'https://i.imgur.com/2GibLR0.png',
            'Клан башлыгы': 'https://i.imgur.com/kMoG0nO.png',
        }

        for name, url in icons.items():
            achievement = Achievement.objects.filter(name=name).first()
            if achievement:
                achievement.icon_url = url
                achievement.save()
                self.stdout.write(self.style.SUCCESS(f'✅ {name} → иконка добавлена'))
            else:
                self.stdout.write(self.style.WARNING(f'❌ {name} не найдено'))

        self.stdout.write(self.style.SUCCESS('🎉 Готово!'))