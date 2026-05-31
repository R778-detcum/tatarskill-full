from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.utils.translation import gettext_lazy as _


class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', _('Начинающий')),
        ('intermediate', _('Средний')),
        ('advanced', _('Продвинутый')),
    ]
    STATUS_CHOICES = [
        ('draft', _('Черновик')),
        ('published', _('Опубликован')),
        ('archived', _('В архиве')),
    ]

    title = models.CharField(_('Название курса'), max_length=200)
    slug = models.SlugField(_('URL-идентификатор'), max_length=200, unique=True, blank=True)
    description = models.TextField(_('Описание курса'))
    short_description = models.CharField(_('Краткое описание'), max_length=300, blank=True)
    level = models.CharField(_('Уровень'), max_length=20, choices=LEVEL_CHOICES, default='beginner')
    duration_weeks = models.PositiveIntegerField(_('Длительность (недель)'), default=4)
    lessons_count = models.PositiveIntegerField(_('Количество уроков'), default=10)
    price = models.DecimalField(_('Цена (₽)'), max_digits=10, decimal_places=2, default=0)
    old_price = models.DecimalField(_('Старая цена (₽)'), max_digits=10, decimal_places=2, blank=True, null=True)
    is_free = models.BooleanField(_('Бесплатный'), default=False)
    icon_class = models.CharField(_('Иконка (Font Awesome)'), max_length=50, default='fas fa-language')
    badge_text = models.CharField(_('Текст бейджа'), max_length=50, blank=True, help_text=_('Например: "🔥 АКЦИЯ"'))
    badge_color = models.CharField(_('Цвет бейджа'), max_length=20, default='warning')
    status = models.CharField(_('Статус'), max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(_('Создан'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлен'), auto_now=True)
    published_at = models.DateTimeField(_('Опубликован'), blank=True, null=True)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    is_official = models.BooleanField(_('Официальный курс'), default=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses',
                               verbose_name=_('Автор курса'))
    additional_tests = models.ManyToManyField('CustomTest', blank=True, related_name='attached_courses',
                                              verbose_name=_('Дополнительные тесты'))

    class Meta:
        verbose_name = _('Курс')
        verbose_name_plural = _('Курсы')
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug or self.slug == '':
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def display_price(self):
        if self.is_free:
            return _('Бесплатно')
        return f'{self.price} ₽'

    @property
    def has_sale(self):
        return self.old_price and self.old_price > self.price


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', verbose_name=_('Курс'))
    title = models.CharField(_('Название урока'), max_length=200)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    section = models.CharField(_('Раздел'), max_length=100, blank=True, help_text=_('Например: Основы, Повседневная речь'))
    video_url = models.URLField(_('Ссылка на видео'), blank=True)
    content = models.TextField(_('Содержание урока'), blank=True, help_text=_('HTML формат'))
    duration_minutes = models.PositiveIntegerField(_('Длительность (минут)'), default=10)
    is_free_preview = models.BooleanField(_('Бесплатный просмотр'), default=False)
    test = models.ForeignKey('CustomTest', on_delete=models.SET_NULL, null=True, blank=True, related_name='lessons',
                             verbose_name=_('Тест к уроку'))

    class Meta:
        verbose_name = _('Урок')
        verbose_name_plural = _('Уроки')
        ordering = ['course', 'order']

    def __str__(self):
        return f'{self.course.title} - {self.title}'


class Community(models.Model):
    name = models.CharField(_('Название сообщества'), max_length=100)
    slug = models.SlugField(_('URL-идентификатор'), max_length=100, unique=True, blank=True)
    icon_class = models.CharField(_('Иконка (Font Awesome)'), max_length=50, default='fas fa-users')
    description = models.CharField(_('Краткое описание'), max_length=200)
    member_count = models.PositiveIntegerField(_('Количество участников'), default=0)
    is_active = models.BooleanField(_('Активно'), default=True)
    is_approved = models.BooleanField(_('Одобрено модератором'), default=True)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    courses = models.ManyToManyField(Course, related_name='communities', blank=True, verbose_name=_('Связанные курсы'))
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_communities',
                              verbose_name=_('Создатель'))
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    is_private = models.BooleanField(_('Закрытое сообщество'), default=False)
    join_password = models.CharField(_('Пароль для входа'), max_length=100, blank=True, help_text=_('Для закрытых сообществ'))
    rules = models.TextField(_('Правила сообщества'), blank=True)
    cover_image = models.URLField(_('Ссылка на обложку'), blank=True)
    tags = models.CharField(_('Теги (через запятую)'), max_length=200, blank=True)
    has_chat = models.BooleanField(_('Чат реального времени'), default=False)

    class Meta:
        verbose_name = _('Сообщество')
        verbose_name_plural = _('Сообщества')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Community.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def user_can_manage(self, user):
        if not user.is_authenticated:
            return False
        if user == self.owner or user.is_superuser:
            return True
        return CommunityMembership.objects.filter(community=self, user=user, role__in=['moderator', 'admin']).exists()


class CommunityMembership(models.Model):
    ROLE_CHOICES = [
        ('member', _('Участник')),
        ('moderator', _('Модератор')),
        ('admin', _('Администратор')),
    ]
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_banned = models.BooleanField(default=False)

    class Meta:
        unique_together = ['community', 'user']


class CommunityPost(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_posts')
    title = models.CharField(_('Заголовок'), max_length=200)
    content = models.TextField(_('Текст поста'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(_('Закреплён'), default=False)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    comments_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f'{self.community.name} - {self.title[:50]}'


class CommunityComment(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_comments')
    content = models.TextField(_('Текст комментария'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)

    class Meta:
        ordering = ['created_at']


class CommunityExternalLink(models.Model):
    LINK_TYPES = [
        ('vkontakte', _('ВКонтакте (группа/паблик)')),
        ('vkontakte_video', _('ВКонтакте видео')),
        ('rutube', _('RUTUBE (канал)')),
        ('website', _('Веб-сайт')),
        ('other', _('Другое')),
    ]
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='external_links')
    link_type = models.CharField(max_length=20, choices=LINK_TYPES, verbose_name=_('Тип ресурса'))
    url = models.URLField(verbose_name=_('Ссылка'))
    title = models.CharField(_('Название'), max_length=100, blank=True)
    icon_class = models.CharField(_('Иконка (Font Awesome)'), max_length=50, blank=True)
    order = models.PositiveIntegerField(_('Порядок'), default=0)
    is_active = models.BooleanField(_('Активна'), default=True)

    class Meta:
        verbose_name = _('Внешняя ссылка')
        verbose_name_plural = _('Внешние ссылки')
        ordering = ['community', 'order', 'link_type']

    def __str__(self):
        return f'{self.community.name} - {self.get_link_type_display()}'


class CommunityChatRoom(models.Model):
    community = models.OneToOneField(Community, on_delete=models.CASCADE, related_name='chat_room')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'Чат сообщества {self.community.name}'


class ChatMessage(models.Model):
    room = models.ForeignKey(CommunityChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']


class Achievement(models.Model):
    name = models.CharField(_('Название достижения'), max_length=100)
    icon_class = models.CharField(_('Иконка (Font Awesome)'), max_length=50, default='fas fa-medal')
    icon_url = models.URLField(_('Ссылка на иконку (Imgur)'), blank=True, null=True)
    description = models.CharField(_('Описание'), max_length=200)
    points = models.PositiveIntegerField(_('Очки'), default=10)
    is_active = models.BooleanField(_('Активно'), default=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Привязанный курс"))

    class Meta:
        verbose_name = _('Достижение')
        verbose_name_plural = _('Достижения')

    def __str__(self):
        return self.name


class Question(models.Model):
    QUESTION_TYPES = [
        ('choice', _('Выбор правильного варианта')),
        ('translate', _('Перевод слова/фразы')),
        ('audio_choice', _('Прослушать и выбрать перевод')),
        ('match', _('Сопоставление')),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions', verbose_name=_('Урок'))
    text = models.TextField(_('Текст вопроса'))
    option1 = models.CharField(_('Вариант 1'), max_length=200)
    option2 = models.CharField(_('Вариант 2'), max_length=200)
    option3 = models.CharField(_('Вариант 3'), max_length=200, blank=True)
    option4 = models.CharField(_('Вариант 4'), max_length=200, blank=True)
    correct_option = models.PositiveSmallIntegerField(_('Номер правильного ответа (1-4)'),
                                                      choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4')])
    explanation = models.TextField(_('Пояснение к ответу'), blank=True)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='choice',
                                     verbose_name=_('Тип вопроса'))
    audio_url = models.URLField(_('Ссылка на аудиофайл'), blank=True, help_text=_('Для типа "audio_choice"'))

    class Meta:
        verbose_name = _('Вопрос теста')
        verbose_name_plural = _('Вопросы тестов')
        ordering = ['id']

    def __str__(self):
        return f'{self.lesson.title} - {self.text[:50]}'

    def get_options(self):
        options = [(1, self.option1), (2, self.option2)]
        if self.option3:
            options.append((3, self.option3))
        if self.option4:
            options.append((4, self.option4))
        return options


class LessonCompletion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='completed_lessons')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)
    test_score = models.PositiveSmallIntegerField(_('Результат теста (%)'), default=0)

    class Meta:
        verbose_name = _('Пройденный урок')
        verbose_name_plural = _('Пройденные уроки')
        unique_together = ['user', 'lesson']

    def __str__(self):
        return f'{self.user.username} - {self.lesson.title}'


class CourseEnrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    lessons_completed = models.PositiveIntegerField(default=0)
    course_xp = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'course']

    def __str__(self):
        return f"{self.user.username} – {self.course.title}"

LEVEL_XP_BOUNDS = {
    1: (0, 59), 2: (60, 119), 3: (120, 199), 4: (200, 299), 5: (300, 449),
    6: (450, 749), 7: (750, 1124), 8: (1125, 1649), 9: (1650, 2249), 10: (2250, 2999),
    11: (3000, 3899), 12: (3900, 4899), 13: (4900, 5999), 14: (6000, 7499), 15: (7500, 8999),
    16: (9000, 10499), 17: (10500, 11999), 18: (12000, 13499), 19: (13500, 14999), 20: (15000, 16999),
    21: (17000, 18999), 22: (19000, 22499), 23: (22500, 25999), 24: (26000, 29999),
}


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(_('О себе'), max_length=500, blank=True)
    phone = models.CharField(_('Телефон'), max_length=20, blank=True)
    city = models.CharField(_('Город'), max_length=100, blank=True)
    total_points = models.PositiveIntegerField(_('Всего очков (XP)'), default=0)
    coins = models.PositiveIntegerField(_('Монеты'), default=0)
    tulips = models.PositiveIntegerField(_('Тюльпаны (премиум валюта)'), default=0)
    lessons_completed = models.PositiveIntegerField(_('Пройдено уроков'), default=0)
    level = models.PositiveIntegerField(_('Уровень'), default=1)
    streak_days = models.PositiveIntegerField(_('Дней подряд'), default=0)
    last_activity_date = models.DateField(_('Дата последней активности'), null=True, blank=True)
    weekly_xp = models.PositiveIntegerField(_('XP за текущую неделю'), default=0)
    max_xp_day = models.PositiveIntegerField(_('Максимум XP за день'), default=0)
    best_league_rank = models.PositiveIntegerField(_('Лучший результат в лиге (место)'), null=True, blank=True)
    is_author = models.BooleanField(_('Автор (может создавать тесты)'), default=False)
    created_at = models.DateTimeField(_('Дата регистрации'), auto_now_add=True)
    last_active = models.DateTimeField(_('Последняя активность'), auto_now=True)
    last_selected_course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True,
                                             verbose_name=_('Последний выбранный курс'))
    dragon_frozen = models.BooleanField(_('Дракон заморожен'), default=False)
    frozen_since = models.DateTimeField(_('Заморожен с'), null=True, blank=True)
    missed_days = models.IntegerField(_('Пропущено дней подряд'), default=0)

    class Meta:
        verbose_name = _('Профиль')
        verbose_name_plural = _('Профили')

    def __str__(self):
        return f'Профиль {self.user.username}'

    def save(self, *args, **kwargs):
        new_level = 1
        xp = self.total_points
        for level, (xp_min, xp_max) in LEVEL_XP_BOUNDS.items():
            if xp_min <= xp <= xp_max:
                new_level = level
                break
            elif xp > xp_max:
                new_level = level + 1
        self.level = new_level
        super().save(*args, **kwargs)


class League(models.Model):
    name = models.CharField(_('Название лиги'), max_length=50)
    tatar_name = models.CharField(_('Название на татарском'), max_length=50)
    rank_order = models.PositiveIntegerField(_('Порядок (1 - низшая)'), unique=True)
    min_users = models.PositiveIntegerField(_('Минимум пользователей для создания'), default=10)
    max_users = models.PositiveIntegerField(_('Максимум пользователей'), default=30)

    class Meta:
        ordering = ['rank_order']

    def __str__(self):
        return self.tatar_name


class LeagueInstance(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='instances')
    instance_number = models.PositiveIntegerField(_('Номер копии'))
    current_week_start = models.DateField(_('Начало текущей недели'), default=timezone.now)

    class Meta:
        unique_together = ['league', 'instance_number']

    def __str__(self):
        return f'{self.league.tatar_name} #{self.instance_number}'


class UserLeagueMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='league_memberships')
    league_instance = models.ForeignKey(LeagueInstance, on_delete=models.CASCADE)
    week_start = models.DateField()
    weekly_xp = models.PositiveIntegerField(_('XP за неделю'), default=0)
    rank = models.PositiveIntegerField(_('Место в лиге'), null=True, blank=True)
    promotion_to = models.ForeignKey(LeagueInstance, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='promoted_from')
    relegation_to = models.ForeignKey(LeagueInstance, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='relegated_from')

    class Meta:
        unique_together = ['user', 'week_start']

    def __str__(self):
        return f'{self.user.username} - {self.league_instance} - неделя {self.week_start}'


class SeasonalEvent(models.Model):
    name = models.CharField(_('Название'), max_length=100)
    tatar_name = models.CharField(_('Название на татарском'), max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    bonus_xp = models.PositiveIntegerField(_('Бонус XP за урок'), default=0)
    bonus_coins = models.PositiveIntegerField(_('Бонус монет'), default=0)

    def __str__(self):
        return self.tatar_name


class AchievementLevel(models.Model):
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='levels')
    level = models.PositiveIntegerField(_('Номер уровня'))
    required_value = models.PositiveIntegerField(_('Необходимое значение'))
    points_reward = models.PositiveIntegerField(_('Награда XP'), default=50)
    coin_reward = models.PositiveIntegerField(_('Награда монет'), default=20)
    tulip_reward = models.PositiveIntegerField(_('Награда тюльпанов'), default=0)
    icon_class = models.CharField(_('Иконка'), max_length=50, blank=True)

    class Meta:
        ordering = ['achievement', 'level']
        unique_together = ['achievement', 'level']

    def __str__(self):
        return f'{self.achievement.name} ур.{self.level}'


class AchievementProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements_progress')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    current_value = models.PositiveIntegerField(_('Текущее значение'), default=0)
    current_level = models.PositiveIntegerField(_('Достигнутый уровень'), default=0)
    achieved_at = models.DateTimeField(_('Дата последнего получения'), null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'achievement']

    def __str__(self):
        return f'{self.user.username} - {self.achievement.name}'

    def check_and_update(self):
        levels = self.achievement.levels.all()
        if not levels:
            return False
        current_max_level = self.current_level
        for level_obj in levels:
            if level_obj.level > current_max_level and self.current_value >= level_obj.required_value:
                profile = self.user.profile
                profile.total_points += level_obj.points_reward
                profile.coins += level_obj.coin_reward
                profile.tulips += level_obj.tulip_reward
                profile.save()
                self.current_level = level_obj.level
                self.achieved_at = timezone.now()
                self.save()
                return True
        return False


class ShopItem(models.Model):
    ITEM_TYPES = [
        ('streak_protect', _('Тумар защиты (защита ударного темпа)')),
        ('xp_boost', _('Курай-ускоритель (удвоение XP на 10 минут)')),
        ('retry_boost', _('Чак-чак энергии (восстановление попыток теста)')),
        ('golden_skullcap', _('Золотая тюбетейка (доступ к супер-тесту)')),
        ('clan_bet', _('Спор батыра (удвоение монет за 7 дней)')),
    ]
    name = models.CharField(_('Название'), max_length=100)
    tatar_name = models.CharField(_('Название на татарском'), max_length=100)
    item_type = models.CharField(_('Тип'), max_length=20, choices=ITEM_TYPES)
    price_coins = models.PositiveIntegerField(_('Цена (монеты)'), default=0)
    price_tulips = models.PositiveIntegerField(_('Цена (тюльпаны)'), default=0)
    duration_minutes = models.PositiveIntegerField(_('Длительность эффекта (мин)'), null=True, blank=True)
    is_active = models.BooleanField(_('Активен'), default=True)
    icon_class = models.CharField(_('Иконка'), max_length=50, default='fas fa-box')

    def __str__(self):
        return self.tatar_name


class UserInventory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_('Количество'), default=1)
    expires_at = models.DateTimeField(_('Действителен до'), null=True, blank=True)
    used_at = models.DateTimeField(_('Активирован'), null=True, blank=True)

    def is_active(self):
        return self.expires_at is None or self.expires_at > timezone.now()


class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    start_date = models.DateTimeField(_('Дата начала'))
    end_date = models.DateTimeField(_('Дата окончания'))
    is_auto_renew = models.BooleanField(_('Автопродление'), default=False)
    is_active = models.BooleanField(_('Активна'), default=True)

    def is_valid(self):
        return self.is_active and self.end_date > timezone.now()


class DailyRewardLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(_('Дата'))
    claimed = models.BooleanField(_('Выдано'), default=False)
    streak_bonus = models.PositiveIntegerField(_('Бонус за стрик'), default=5)

    class Meta:
        unique_together = ['user', 'date']


class CourseReview(models.Model):
    RATING_CHOICES = [
        (1, '★☆☆☆☆ (1)'),
        (2, '★★☆☆☆ (2)'),
        (3, '★★★☆☆ (3)'),
        (4, '★★★★☆ (4)'),
        (5, '★★★★★ (5)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_reviews', verbose_name=_('Пользователь'))
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews', verbose_name=_('Курс'))
    rating = models.PositiveSmallIntegerField(_('Оценка'), choices=RATING_CHOICES)
    comment = models.TextField(_('Текст отзыва'), max_length=1000)
    is_approved = models.BooleanField(_('Одобрен'), default=False)
    created_at = models.DateTimeField(_('Дата'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Обновлён'), auto_now=True)

    class Meta:
        verbose_name = _('Отзыв на курс')
        verbose_name_plural = _('Отзывы на курсы')
        ordering = ['-created_at']
        unique_together = ['user', 'course']

    def __str__(self):
        return f'{self.user.username} — {self.course.title} — {self.rating}★'


class CustomTest(models.Model):
    STATUS_CHOICES = [
        ('draft', _('Черновик')),
        ('moderation', _('На модерации')),
        ('approved', _('Опубликован')),
        ('rejected', _('Отклонён')),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', _('Лёгкий')),
        ('medium', _('Средний')),
        ('hard', _('Сложный')),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_tests', verbose_name=_('Автор'))
    title = models.CharField(max_length=200, verbose_name=_('Название теста'))
    subject = models.CharField(max_length=100, verbose_name=_('Предмет'), default='Татарский язык')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medium', verbose_name=_('Сложность'))
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name=_('Привязанный курс (опционально)'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name=_('Статус'))
    reward_coins_per_question = models.PositiveIntegerField(default=5,
                                                            verbose_name=_('Награда (монет) за 1 правильный ответ'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.title} — {self.author.username}'

    class Meta:
        verbose_name = _('Пользовательский тест')
        verbose_name_plural = _('Пользовательские тесты')
        ordering = ['-created_at']


class CustomQuestion(models.Model):
    test = models.ForeignKey(CustomTest, on_delete=models.CASCADE, related_name='questions', verbose_name=_('Тест'))
    text = models.TextField(verbose_name=_('Текст вопроса'))
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200, blank=True)
    option4 = models.CharField(max_length=200, blank=True)
    correct_option = models.PositiveSmallIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4')],
                                                      verbose_name=_('Правильный ответ (1-4)'))
    explanation = models.TextField(blank=True, verbose_name=_('Пояснение'))

    def __str__(self):
        return f'{self.test.title} — вопрос {self.id}'


class CustomTestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_test_results')
    test = models.ForeignKey(CustomTest, on_delete=models.CASCADE, related_name='results')
    score = models.PositiveIntegerField(verbose_name=_('Правильных ответов'))
    total_questions = models.PositiveIntegerField(verbose_name=_('Всего вопросов'))
    earned_coins = models.PositiveIntegerField(verbose_name=_('Заработано монет'), default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} — {self.test.title}: {self.score}/{self.total_questions}'

    class Meta:
        verbose_name = _('Результат теста')
        verbose_name_plural = _('Результаты тестов')
        ordering = ['-completed_at']


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Friendship(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Ожидает подтверждения')),
        ('accepted', _('Друзья')),
        ('rejected', _('Отклонена')),
        ('blocked', _('Заблокирован')),
    ]

    from_user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='friend_requests_sent',
        verbose_name=_('Отправитель')
    )
    to_user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='friend_requests_received',
        verbose_name=_('Получатель')
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', verbose_name=_('Статус')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))

    class Meta:
        verbose_name = _('Дружба')
        verbose_name_plural = _('Дружбы')
        unique_together = ['from_user', 'to_user']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.from_user.username} → {self.to_user.username} ({self.status})'

    def accept(self):
        self.status = 'accepted'
        self.save()

    def reject(self):
        self.status = 'rejected'
        self.save()

    @staticmethod
    def are_friends(user1, user2):
        if user1 == user2:
            return False
        return Friendship.objects.filter(
            Q(from_user=user1, to_user=user2, status='accepted') |
            Q(from_user=user2, to_user=user1, status='accepted')
        ).exists()