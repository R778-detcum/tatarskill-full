from django.core.management.base import BaseCommand
from django.db.models import Q
from django.contrib.auth.models import User
from main.models import Friendship, LessonCompletion, AchievementProgress
from main.services.achievement_service import AchievementService


class Command(BaseCommand):
    help = 'Выдаёт достижения существующим пользователям на основе их текущих данных'

    def handle(self, *args, **options):
        users = User.objects.all()

        for user in users:
            profile = user.profile
            self.stdout.write(f'Обработка: {user.username}')

            # 1. Достижение за регистрацию (Беренче адым)
            AchievementService.check_first_lesson(user)

            # 2. Достижение за пройденные уроки
            AchievementService.check_lessons_achievement(user, profile.lessons_completed)

            # 3. Достижение за XP
            AchievementService.check_xp_achievement(user, profile.total_points)

            # 4. Достижение за стрик дней
            AchievementService.check_streak_achievement(user, profile.streak_days)

            # 5. Достижение за друзей
            friends_count = Friendship.objects.filter(
                Q(from_user=user, status='accepted') |
                Q(to_user=user, status='accepted')
            ).count()
            if friends_count > 0:
                AchievementService.check_friends_achievement(user, friends_count)

            # 6. Достижение Снайпер (90%+ в тесте)
            perfect_count = LessonCompletion.objects.filter(
                user=user,
                test_score__gte=90
            ).count()
            if perfect_count > 0:
                AchievementService.check_sniper_achievement(user, perfect_count)

            # 7. Достижения за ночное и утреннее время
            night_lessons = LessonCompletion.objects.filter(
                user=user,
                completed_at__hour__gte=23
            ).exists()
            if night_lessons:
                from django.utils import timezone
                AchievementService.check_night_owl(user, timezone.now())

            morning_lessons = LessonCompletion.objects.filter(
                user=user,
                completed_at__hour__lt=7
            ).exists()
            if morning_lessons:
                from django.utils import timezone
                AchievementService.check_early_bird(user, timezone.now())

        self.stdout.write(self.style.SUCCESS('✅ Все старые пользователи обработаны!'))