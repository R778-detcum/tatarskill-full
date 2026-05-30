from django.utils import timezone


class DragonService:

    @staticmethod
    def check_streak(user):
        profile = user.profile
        if profile.dragon_frozen:
            return False

        last_active = profile.last_activity_date
        if last_active:
            days_since_last = (timezone.now().date() - last_active).days
            if days_since_last >= 3:
                profile.dragon_frozen = True
                profile.frozen_since = timezone.now()
                profile.missed_days = days_since_last
                profile.save()
                return True
            elif days_since_last >= 1:
                profile.missed_days = days_since_last
                profile.save()
        return False

    @staticmethod
    def unfreeze_dragon(user, payment_type='money'):
        from main.models import ShopItem, UserInventory
        from django.utils import timezone
        from datetime import timedelta
        from .achievement_service import AchievementService

        profile = user.profile

        if not profile.dragon_frozen:
            return {'success': False, 'message': 'Дракон не замёрз!'}

        if payment_type == 'coins':
            if profile.coins >= 500:
                profile.coins -= 500
                profile.dragon_frozen = False
                profile.frozen_since = None
                profile.missed_days = 0
                profile.save()
                return {'success': True, 'message': 'Дракон разморожен за 500 монет! 🔥'}
            else:
                return {'success': False, 'message': f'Не хватает монет! Нужно 500, у вас {profile.coins}'}

        elif payment_type == 'money':
            # Разморозка за 199₽ + БОНУСЫ
            profile.dragon_frozen = False
            profile.frozen_since = None
            profile.missed_days = 0

            # БОНУСЫ:
            profile.coins += 500  # +500 монет
            profile.total_points += 1000  # +1000 XP

            # Добавляем Тумар защиты в инвентарь
            talisman = ShopItem.objects.filter(item_type='streak_protect', is_active=True).first()
            if talisman:
                UserInventory.objects.create(
                    user=user,
                    item=talisman,
                    quantity=1,
                    expires_at=timezone.now() + timedelta(days=30)
                )

            profile.save()

            # Выдаём достижение "Спаситель дракона"
            try:
                AchievementService.check_and_award(user, 'Спаситель дракона', 1)
            except Exception as e:
                print(f'Ошибка выдачи достижения: {e}')

            return {
                'success': True,
                'message': '🎉 Дракон разморожен! Ты получил: +500 монет, +1000 XP, 🛡️ Тумар защиты и достижение "Спаситель дракона"!'
            }

        return {'success': False, 'message': 'Неизвестный способ оплаты'}