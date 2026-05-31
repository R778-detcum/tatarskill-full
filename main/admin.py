from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Course, Lesson, Community, CommunityMembership, CommunityPost, CommunityComment, CommunityExternalLink,
    Achievement, Profile, Question, LessonCompletion, League, LeagueInstance,
    UserLeagueMembership, SeasonalEvent, AchievementLevel, AchievementProgress,
    ShopItem, UserInventory, UserSubscription, DailyRewardLog, CustomTest,
    CustomQuestion, CustomTestResult, CourseReview
)


class CommunityMembershipInline(admin.TabularInline):
    model = CommunityMembership
    extra = 0
    fields = ['user', 'role', 'is_banned', 'joined_at']
    readonly_fields = ['joined_at']


class CommunityExternalLinkInline(admin.TabularInline):
    model = CommunityExternalLink
    extra = 1
    fields = ['link_type', 'url', 'title', 'icon_class', 'order', 'is_active']


class CommunityPostInline(admin.TabularInline):
    model = CommunityPost
    extra = 0
    fields = ['title', 'author', 'is_pinned', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'owner', 'member_count', 'is_active', 'has_chat', 'order', 'created_at']
    list_filter = ['is_active', 'is_private', 'has_chat', 'created_at']
    search_fields = ['name', 'description', 'owner__username']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'order', 'has_chat']
    inlines = [CommunityMembershipInline, CommunityExternalLinkInline, CommunityPostInline]
    fieldsets = (
        (_('Основное'), {'fields': ('name', 'slug', 'description', 'icon_class', 'cover_image')}),
        (_('Доступ'), {'fields': ('is_active', 'is_private', 'join_password', 'owner')}),
        (_('Чат'), {'fields': ('has_chat',)}),
        (_('Дополнительно'), {'fields': ('rules', 'tags', 'order', 'member_count', 'courses')}),
    )
    filter_horizontal = ['courses']


@admin.register(CommunityMembership)
class CommunityMembershipAdmin(admin.ModelAdmin):
    list_display = ['community', 'user', 'role', 'is_banned', 'joined_at']
    list_filter = ['role', 'is_banned', 'community']
    search_fields = ['user__username', 'community__name']


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'community', 'author', 'created_at', 'is_pinned', 'comments_count']
    list_filter = ['community', 'is_pinned']
    search_fields = ['title', 'content', 'author__username']


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'created_at']
    list_filter = ['post__community']
    search_fields = ['content', 'author__username']


@admin.register(CommunityExternalLink)
class CommunityExternalLinkAdmin(admin.ModelAdmin):
    list_display = ['community', 'link_type', 'url', 'is_active', 'order']
    list_filter = ['link_type', 'is_active', 'community']
    search_fields = ['community__name', 'url']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_points', 'coins', 'tulips', 'level', 'streak_days', 'lessons_completed', 'is_author', 'created_at']
    search_fields = ['user__username', 'user__email']
    list_editable = ['coins', 'tulips', 'is_author']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'level', 'price', 'is_free', 'status', 'lessons_count', 'is_official', 'created_at']
    list_filter = ['status', 'level', 'is_free', 'is_official', 'created_at']
    search_fields = ['title', 'description', 'author__username']
    list_editable = ['status', 'is_official']
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (_('Основная информация'), {'fields': ('title', 'slug', 'description', 'short_description', 'author')}),
        (_('Детали курса'), {'fields': ('level', 'duration_weeks', 'lessons_count')}),
        (_('Цена и акции'), {'fields': ('price', 'old_price', 'is_free'), 'classes': ('collapse',)}),
        (_('Визуальное оформление'), {'fields': ('icon_class', 'badge_text', 'badge_color'), 'classes': ('collapse',)}),
        (_('Статус и даты'), {'fields': ('status', 'order', 'published_at', 'is_official'), 'classes': ('collapse',)}),
    )
    actions = ['make_published', 'make_draft', 'make_official', 'make_unofficial']

    def make_published(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='published', published_at=timezone.now())
    make_published.short_description = _('Опубликовать выбранные курсы')

    def make_draft(self, request, queryset):
        queryset.update(status='draft')
    make_draft.short_description = _('Снять с публикации')

    def make_official(self, request, queryset):
        queryset.update(is_official=True)
    make_official.short_description = _('Сделать официальными')

    def make_unofficial(self, request, queryset):
        queryset.update(is_official=False)
    make_unofficial.short_description = _('Сделать народными')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'section', 'order', 'duration_minutes', 'is_free_preview']
    list_filter = ['course', 'section', 'is_free_preview']
    search_fields = ['title', 'content']
    list_editable = ['order', 'duration_minutes']


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'points', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_editable = ['points', 'is_active']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'lesson', 'correct_option']
    list_filter = ['lesson']
    search_fields = ['text']


@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'test_score', 'completed_at']
    list_filter = ['lesson__course', 'lesson']
    search_fields = ['user__username', 'lesson__title']


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['tatar_name', 'rank_order', 'min_users', 'max_users']


@admin.register(LeagueInstance)
class LeagueInstanceAdmin(admin.ModelAdmin):
    list_display = ['league', 'instance_number', 'current_week_start']


@admin.register(UserLeagueMembership)
class UserLeagueMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'league_instance', 'week_start', 'weekly_xp', 'rank']


@admin.register(SeasonalEvent)
class SeasonalEventAdmin(admin.ModelAdmin):
    list_display = ['tatar_name', 'start_date', 'end_date', 'is_active']


@admin.register(AchievementLevel)
class AchievementLevelAdmin(admin.ModelAdmin):
    list_display = ['achievement', 'level', 'required_value', 'points_reward', 'coin_reward']


@admin.register(AchievementProgress)
class AchievementProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'current_value', 'current_level']


@admin.register(ShopItem)
class ShopItemAdmin(admin.ModelAdmin):
    list_display = ['tatar_name', 'item_type', 'price_coins', 'price_tulips', 'is_active']


@admin.register(UserInventory)
class UserInventoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'item', 'quantity', 'expires_at', 'used_at']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'start_date', 'end_date', 'is_active']


@admin.register(DailyRewardLog)
class DailyRewardLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'claimed', 'streak_bonus']


@admin.register(CustomTest)
class CustomTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'difficulty', 'created_at']
    list_filter = ['status', 'difficulty']
    search_fields = ['title', 'author__username']
    list_editable = ['status']


@admin.register(CustomQuestion)
class CustomQuestionAdmin(admin.ModelAdmin):
    list_display = ['test', 'text', 'correct_option']


@admin.register(CustomTestResult)
class CustomTestResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'test', 'score', 'earned_coins', 'completed_at']
    list_filter = ['test', 'user']


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'course', 'rating']
    search_fields = ['user__username', 'course__title', 'comment']
    list_editable = ['is_approved']
    list_display_links = ['user']