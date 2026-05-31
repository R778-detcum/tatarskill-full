from django.db.models import Q
from django.utils import timezone
from main.models import Achievement, AchievementProgress, AchievementLevel, User


class AchievementService:
    """Сервис для проверки и выдачи достижений"""

    @staticmethod
    def check_and_award(user, achievement_name, current_value, save=True):
        """
        Проверяет и выдает достижения пользователю

        Args:
            user: объект User
            achievement_name: название достижения (например 'Тырыш укучы')
            current_value: текущее значение (сколько уроков пройдено, дней стрика и т.д.)
            save: сохранять ли изменения сразу
        """
        try:
            achievement = Achievement.objects.get(name=achievement_name, is_active=True)
        except Achievement.DoesNotExist:
            return False

        progress, created = AchievementProgress.objects.get_or_create(
            user=user,
            achievement=achievement,
            defaults={'current_value': current_value, 'current_level': 0}
        )

        if not created and progress.current_value >= current_value:
            return False

        progress.current_value = current_value

        levels = achievement.levels.all().order_by('level')
        new_level = progress.current_level
        awarded_levels = []

        for level in levels:
            if level.level > new_level and current_value >= level.required_value:
                profile = user.profile
                profile.total_points += level.points_reward
                profile.coins += level.coin_reward
                profile.save()

                new_level = level.level
                awarded_levels.append(level.level)

        if new_level > progress.current_level:
            progress.current_level = new_level
            progress.achieved_at = timezone.now()

        if save:
            progress.save()

        return awarded_levels

    @staticmethod
    def check_lessons_achievement(user, lessons_count):
        return AchievementService.check_and_award(user, 'Тырыш укучы', lessons_count)

    @staticmethod
    def check_streak_achievement(user, streak_days):
        return AchievementService.check_and_award(user, 'Идеаль тәртип', streak_days)

    @staticmethod
    def check_friends_achievement(user, friends_count):
        return AchievementService.check_and_award(user, 'Дуслык көче', friends_count)

    @staticmethod
    def check_xp_achievement(user, total_xp):
        return AchievementService.check_and_award(user, 'Алтын тырышлык', total_xp)

    @staticmethod
    def check_sniper_achievement(user, perfect_tests_count):
        return AchievementService.check_and_award(user, 'Мәргән', perfect_tests_count)

    @staticmethod
    def check_first_lesson(user):
        return AchievementService.check_and_award(user, 'Беренче адым', 1)

    @staticmethod
    def check_night_owl(user, lesson_completed_at):
        hour = lesson_completed_at.hour
        if hour >= 23 or hour < 5:
            return AchievementService.check_and_award(user, 'Төнге өкө', 1)
        return False

    @staticmethod
    def check_early_bird(user, lesson_completed_at):
        hour = lesson_completed_at.hour
        if hour < 7:
            return AchievementService.check_and_award(user, 'Иртә кошы', 1)
        return False

    @staticmethod
    def check_speed_demon(user, lesson, seconds_spent):
        return AchievementService.check_and_award(user, 'Яшен тизлеге', seconds_spent)