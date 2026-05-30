from django.core.management.base import BaseCommand
from main.models import Achievement, AchievementLevel


class Command(BaseCommand):
    help = 'Загружает все достижения из документа'

    def handle(self, *args, **options):
        # Словарь с достижениями: название, иконка, описание, уровни
        achievements_data = {
            # 1. Первый шаг (без уровней)
            'Беренче адым': {
                'icon_url': 'https://i.imgur.com/XohRe4a.png',
                'icon_class': 'fas fa-star',
                'description': 'Первый шаг',
                'levels': []
            },
            # 2. Прилежный ученик (5 уровней)
            'Тырыш укучы': {
                'icon_url': 'https://i.imgur.com/TIof7mx.png',
                'icon_class': 'fas fa-graduation-cap',
                'description': 'Прилежный ученик',
                'levels': [10, 25, 50, 100, 250]
            },
            # 3. Идеальный порядок (8 уровней)
            'Идеаль тәртип': {
                'icon_url': 'https://i.imgur.com/JH396An.png',
                'icon_class': 'fas fa-calendar-alt',
                'description': 'Идеальный порядок',
                'levels': [3, 7, 14, 30, 60, 100, 180, 365]
            },
            # 4. Мастер слова
            'Сүз остасы': {
                'icon_url': 'https://i.imgur.com/GecHVPf.png',
                'icon_class': 'fas fa-language',
                'description': 'Мастер слова',
                'levels': [50, 100, 250, 500, 1000]
            },
            # 5. Математический богатырь
            'Математик батыр': {
                'icon_url': 'https://i.imgur.com/I9Iegaw.png',
                'icon_class': 'fas fa-calculator',
                'description': 'Математический богатырь',
                'levels': [100, 500, 2000]
            },
            # 6. Любитель истории
            'Тарих сөюче': {
                'icon_url': 'https://i.imgur.com/YiqIJXi.png',
                'icon_class': 'fas fa-history',
                'description': 'Любитель истории',
                'levels': [5, 15, 30]
            },
            # 7. Снайпер
            'Мәргән': {
                'icon_url': 'https://i.imgur.com/UNjYnrd.png',
                'icon_class': 'fas fa-bullseye',
                'description': 'Снайпер',
                'levels': [1, 5, 10, 25, 50, 100, 200, 500, 1000]
            },
            # 8. Золотое перо
            'Алтын каләм': {
                'icon_url': 'https://i.imgur.com/7HckzBJ.png',
                'icon_class': 'fas fa-feather-alt',
                'description': 'Золотое перо',
                'levels': [1, 5, 10]
            },
            # 9. Жемчужина знаний
            'Белем энҗесе': {
                'icon_url': 'https://i.imgur.com/6pikUYv.png',
                'icon_class': 'fas fa-gem',
                'description': 'Жемчужина знаний (50 правильных ответов подряд)',
                'levels': []
            },
            # 10. Золотое усердие
            'Алтын тырышлык': {
                'icon_url': 'https://i.imgur.com/kMoG0nO.png',
                'icon_class': 'fas fa-trophy',
                'description': 'Золотое усердие',
                'levels': [500, 1000, 5000, 10000, 50000]
            },
            # 11. Ночная сова
            'Төнге өкө': {
                'icon_url': 'https://i.imgur.com/rMm56YO.png',
                'icon_class': 'fas fa-moon',
                'description': 'Ночная сова',
                'levels': []
            },
            # 12. Ранняя пташка
            'Иртә кошы': {
                'icon_url': 'https://i.imgur.com/kOdr04h.png',
                'icon_class': 'fas fa-sun',
                'description': 'Ранняя пташка',
                'levels': []
            },
            # 13. Скорость молнии
            'Яшен тизлеге': {
                'icon_url': 'https://i.imgur.com/JcpbVOv.png',
                'icon_class': 'fas fa-bolt',
                'description': 'Скорость молнии',
                'levels': [60, 45, 30]
            },
            # 14. Сила дружбы
            'Дуслык көче': {
                'icon_url': 'https://i.imgur.com/2GibLR0.png',
                'icon_class': 'fas fa-users',
                'description': 'Сила дружбы',
                'levels': [1, 5, 10]
            },
            # 15. Вождь клана
            'Клан башлыгы': {
                'icon_url': 'https://i.imgur.com/kMoG0nO.png',
                'icon_class': 'fas fa-crown',
                'description': 'Вождь клана (создать сообщество с 10+ участниками)',
                'levels': []
            },
        }

        for name, data in achievements_data.items():
            achievement, created = Achievement.objects.get_or_create(
                name=name,
                defaults={
                    'icon_class': data['icon_class'],
                    'icon_url': data['icon_url'],
                    'description': data['description'],
                    'points': 50,  # базовые очки
                    'is_active': True,
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Создано достижение: {name}'))
            else:
                # Обновляем существующие
                achievement.icon_url = data['icon_url']
                achievement.save()
                self.stdout.write(self.style.WARNING(f'🔄 Обновлено достижение: {name}'))

            # Создаём уровни
            if data['levels']:
                for level_num, req_value in enumerate(data['levels'], start=1):
                    level, level_created = AchievementLevel.objects.get_or_create(
                        achievement=achievement,
                        level=level_num,
                        defaults={
                            'required_value': req_value,
                            'points_reward': 50 * level_num,
                            'coin_reward': 20 * level_num,
                        }
                    )
                    if level_created:
                        self.stdout.write(f'   └─ Уровень {level_num}: {req_value}')
            else:
                # Достижение без уровней (один уровень)
                level, level_created = AchievementLevel.objects.get_or_create(
                    achievement=achievement,
                    level=1,
                    defaults={
                        'required_value': 1,
                        'points_reward': 50,
                        'coin_reward': 20,
                    }
                )
                if level_created:
                    self.stdout.write(f'   └─ Базовый уровень')

        self.stdout.write(self.style.SUCCESS('\n🎉 Все достижения загружены!'))