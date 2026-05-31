import json
from datetime import timedelta
from django.db import models
from django import forms
from .services.achievement_service import AchievementService
from .services.dragon_service import DragonService
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count, Q, Avg
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy
from django.utils import translation
from django.conf import settings


from .forms import (
    CourseForm, LessonForm, CommunityForm, CommunityPostForm,
    CommunityCommentForm, CommunityExternalLinkForm
)
from .models import (
    Course, Lesson, Community, CommunityMembership, CommunityPost,
    CommunityComment, CommunityExternalLink, CommunityChatRoom, ChatMessage,
    Achievement, Question, LessonCompletion, Profile,
    League, LeagueInstance, UserLeagueMembership, SeasonalEvent,
    AchievementLevel, AchievementProgress, ShopItem, UserInventory,
    UserSubscription, DailyRewardLog, LEVEL_XP_BOUNDS, CourseEnrollment,
    CourseReview, CustomTest, CustomQuestion, CustomTestResult, Friendship
)
from .services.mistral_service import MistralService
from .services.dragon_service import DragonService

slugify.allow_unicode = True

mistral_service = MistralService()


def home(request):

    lang = request.GET.get('lang')
    if lang and lang in dict(settings.LANGUAGES):
        translation.activate(lang)
        request.session[translation.LANGUAGE_SESSION_KEY] = lang
        # Перенаправляем на ту же страницу без параметра lang, чтобы он не мешал
        return redirect(request.path)

    if request.user.is_authenticated:
        DragonService.check_streak(request.user)

    available_courses = []
    current_course = None

    if request.user.is_authenticated:
        enrolled_courses = Course.objects.filter(
            enrollments__user=request.user,
            status='published'
        ).distinct().order_by('order', '-created_at')
        available_courses = list(enrolled_courses)

        course_slug = request.GET.get('course_id')
        if course_slug:
            try:
                current_course = Course.objects.get(slug=course_slug, status='published')
                request.session['current_course_slug'] = course_slug
                profile = request.user.profile
                profile.last_selected_course = current_course
                profile.save(update_fields=['last_selected_course'])
            except Course.DoesNotExist:
                pass

        if not current_course and 'current_course_slug' in request.session:
            try:
                current_course = Course.objects.get(slug=request.session['current_course_slug'], status='published')
            except Course.DoesNotExist:
                pass

        if not current_course and request.user.profile.last_selected_course:
            current_course = request.user.profile.last_selected_course
            if current_course.status != 'published':
                current_course = None

        if not current_course and available_courses:
            current_course = available_courses[0]
            request.user.profile.last_selected_course = current_course
            request.user.profile.save(update_fields=['last_selected_course'])
            request.session['current_course_slug'] = current_course.slug
    else:
        available_courses = Course.objects.filter(status='published').order_by('order', '-created_at')
        if available_courses:
            current_course = available_courses[0]

    if not current_course:
        current_course = Course.objects.filter(status='published').first()

    leaderboard = []
    if current_course:
        enrollments = CourseEnrollment.objects.filter(course=current_course).select_related('user').order_by('-course_xp')[:3]
        for idx, enrollment in enumerate(enrollments, start=1):
            leaderboard.append({
                'rank': idx,
                'username': enrollment.user.username,
                'lessons_completed': enrollment.lessons_completed,
                'course_xp': enrollment.course_xp,
            })

    communities = []
    if current_course:
        communities = current_course.communities.filter(is_active=True).exclude(slug__isnull=True).exclude(
            slug='').order_by('order', 'name')

    courses_list = Course.objects.filter(status='published').order_by('order', '-created_at')
    achievements = Achievement.objects.filter(is_active=True)

    if request.user.is_authenticated:
        user_achievements_for_home = AchievementProgress.objects.filter(
            user=request.user,
            current_level__gt=0
        ).select_related('achievement')[:6]
    else:
        user_achievements_for_home = []

    context = {
        'courses': courses_list,
        'communities': communities,
        'achievements': achievements,
        'clan_leaderboard': leaderboard,
        'current_course': current_course,
        'available_courses': available_courses,
        'leaderboard': leaderboard,
        'user_achievements_for_home': user_achievements_for_home,
    }
    return render(request, 'index.html', context)


def education(request):
    courses = Course.objects.filter(status='published').order_by('order', '-created_at')
    return render(request, 'education.html', {'courses': courses})


def community(request):
    communities = Community.objects.filter(is_active=True).order_by('order', 'name')
    return render(request, 'community.html', {'communities': communities})


def ratings(request):
    return HttpResponse(_("Рейтинги учеников - в разработке"))


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 != password2:
            messages.error(request, _('Пароли не совпадают'))
            return redirect('register')
        if User.objects.filter(username=username).exists():
            messages.error(request, _('Пользователь с таким именем уже существует'))
            return redirect('register')
        if User.objects.filter(email=email).exists():
            messages.error(request, _('Пользователь с таким email уже существует'))
            return redirect('register')
        user = User.objects.create_user(username=username, email=email, password=password1)
        login(request, user)
        AchievementService.check_first_lesson(user)
        messages.success(request, _('Регистрация успешно завершена!'))
        return redirect('home')
    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, _('Добро пожаловать, {username}!').format(username=user.username))
            return redirect('home')
        else:
            messages.error(request, _('Неверное имя пользователя или пароль'))
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    list(messages.get_messages(request))
    return redirect('home')


@login_required
def profile_view(request):
    user_achievements = AchievementProgress.objects.filter(
        user=request.user,
        current_level__gt=0
    ).select_related('achievement')

    user_achievement_ids = list(user_achievements.values_list('achievement_id', flat=True))

    all_achievements = Achievement.objects.filter(is_active=True).exclude(id__in=user_achievement_ids)

    user_communities = Community.objects.filter(owner=request.user).order_by('-created_at')

    context = {
        'user': request.user,
        'user_achievements': user_achievements,
        'all_achievements': all_achievements,
        'user_communities': user_communities,
    }
    return render(request, 'profile.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])
        if not user_message:
            return JsonResponse({'error': _('Сообщение не может быть пустым')}, status=400)
        result = mistral_service.get_response(user_message, conversation_history)
        if result['success']:
            return JsonResponse({'response': result['response'], 'history': result['history']})
        else:
            return JsonResponse({'error': result['error']}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def all_courses(request):
    courses = Course.objects.filter(status='published').order_by('order', '-created_at')
    return render(request, 'courses.html', {'courses': courses})


def all_communities(request):
    communities = Community.objects.filter(is_active=True).order_by('order', 'name')
    return render(request, 'communities.html', {'communities': communities})


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, status='published')
    lessons = course.lessons.all().order_by('order')
    completed_lessons = set()
    if request.user.is_authenticated:
        completed_lessons = set(
            LessonCompletion.objects.filter(user=request.user, lesson__course=course).values_list('lesson_id',
                                                                                                  flat=True)
        )
    unlocked_lessons = set()
    if request.user.is_authenticated:
        unlocked_lessons.update(completed_lessons)
        first_lesson = lessons.first()
        if first_lesson and first_lesson.id not in completed_lessons:
            unlocked_lessons.add(first_lesson.id)
        last_completed = None
        for lesson in lessons:
            if lesson.id in completed_lessons:
                last_completed = lesson
        if last_completed:
            next_lesson = Lesson.objects.filter(course=course, order=last_completed.order + 1).first()
            if next_lesson and next_lesson.id not in completed_lessons:
                unlocked_lessons.add(next_lesson.id)
    else:
        if lessons:
            unlocked_lessons.add(lessons[0].id)
    total_lessons = course.lessons_count
    completed_count = len(completed_lessons)
    progress_percent = (completed_count / total_lessons) * 100 if total_lessons > 0 else 0
    avg_rating = course.reviews.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg'] or 0
    avg_rating = round(avg_rating, 1)
    context = {
        'course': course,
        'lessons': lessons,
        'completed_lessons': completed_lessons,
        'unlocked_lessons': unlocked_lessons,
        'progress_percent': round(progress_percent, 1),
        'avg_rating': avg_rating,
    }
    return render(request, 'course_detail.html', context)


def check_lesson_access(user, lesson):
    if not user.is_authenticated:
        return lesson.order == 1
    if lesson.order == 1:
        return True
    previous_lesson = Lesson.objects.filter(course=lesson.course, order=lesson.order - 1).first()
    if previous_lesson:
        return LessonCompletion.objects.filter(user=user, lesson=previous_lesson).exists()
    return False


@login_required
def lesson_detail(request, course_slug, order):
    course = get_object_or_404(Course, slug=course_slug, status='published')
    lesson = get_object_or_404(Lesson, course=course, order=order)
    if not check_lesson_access(request.user, lesson):
        messages.error(request, _('Этот урок ещё не доступен. Пройдите предыдущие уроки.'))
        return redirect('course_detail', slug=course.slug)
    has_test = lesson.questions.exists()
    is_completed = LessonCompletion.objects.filter(user=request.user, lesson=lesson).exists()
    context = {
        'course': course,
        'lesson': lesson,
        'has_test': has_test,
        'is_completed': is_completed,
    }
    return render(request, 'lesson_detail.html', context)


@login_required
def take_test(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if not check_lesson_access(request.user, lesson):
        messages.error(request, _('Этот урок ещё не доступен.'))
        return redirect('course_detail', slug=lesson.course.slug)
    questions = lesson.questions.all()
    if not questions.exists():
        messages.error(request, _('Для этого урока ещё нет теста.'))
        return redirect('lesson_detail', course_slug=lesson.course.slug, order=lesson.order)
    context = {'lesson': lesson, 'questions': questions}
    return render(request, 'test_duo.html', context)

@login_required
def check_answer_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': _('Метод не поддерживается')}, status=405)
    data = json.loads(request.body)
    question_id = data.get('question_id')
    selected = data.get('selected')
    answer_text = data.get('answer_text', '').strip()
    question = get_object_or_404(Question, id=question_id)
    is_correct = False
    if question.question_type == 'translate':
        correct_text = question.option1.strip().lower()
        is_correct = (answer_text.lower() == correct_text)
    else:
        if selected and int(selected) == question.correct_option:
            is_correct = True
    return JsonResponse({'correct': is_correct, 'explanation': question.explanation})


@login_required
def submit_test(request, lesson_id):
    if request.method != 'POST':
        return JsonResponse({'error': _('Метод не поддерживается')}, status=405)

    lesson = get_object_or_404(Lesson, id=lesson_id)

    if not check_lesson_access(request.user, lesson):
        messages.error(request, _('Этот урок ещё не доступен.'))
        return redirect('course_detail', slug=lesson.course.slug)

    questions = list(lesson.questions.all())
    total_questions = len(questions)
    correct_count = 0

    for question in questions:
        answer_key = f'question_{question.id}'
        selected_option = request.POST.get(answer_key)
        if selected_option and int(selected_option) == question.correct_option:
            correct_count += 1

    percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0

    completion, created = LessonCompletion.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'test_score': percentage}
    )

    if not created and completion.test_score < percentage:
        completion.test_score = percentage
        completion.save()

    enrollment, _ = CourseEnrollment.objects.get_or_create(
        user=request.user,
        course=lesson.course
    )
    unique_lessons_count = LessonCompletion.objects.filter(
        user=request.user,
        lesson__course=lesson.course
    ).values('lesson').distinct().count()
    enrollment.lessons_completed = unique_lessons_count

    if created:
        enrollment.course_xp += 150
        enrollment.save()
    else:
        enrollment.save()

    if created:
        profile = request.user.profile
        profile.total_points += 150
        profile.coins += 50
        profile.lessons_completed += 1
        profile.save()

        today = timezone.now().date()

        if profile.last_activity_date:
            days_diff = (today - profile.last_activity_date).days
            if days_diff == 1:
                profile.streak_days += 1
            elif days_diff > 1:
                profile.streak_days = 1
            else:
                pass
        else:
            profile.streak_days = 1

        profile.last_activity_date = today
        profile.save()

        if profile.dragon_frozen:
            profile.dragon_frozen = False
            profile.frozen_since = None
            profile.missed_days = 0
            profile.save()
            messages.info(request, _('❄️ Твой дракон разморозился! Продолжай заниматься, чтобы он рос! 🔥'))

        AchievementService.check_lessons_achievement(request.user, profile.lessons_completed)
        AchievementService.check_xp_achievement(request.user, profile.total_points)
        AchievementService.check_streak_achievement(request.user, profile.streak_days)
        now = timezone.now()
        AchievementService.check_night_owl(request.user, now)
        AchievementService.check_early_bird(request.user, now)
        if percentage >= 90:
            perfect_count = LessonCompletion.objects.filter(
                user=request.user,
                test_score__gte=90
            ).count()
            AchievementService.check_sniper_achievement(request.user, perfect_count)

        messages.success(request, _('🎉 Урок пройден! +150 очков опыта, +50 монет.'))
    else:
        messages.info(request, _('Тест пройден повторно. Результат: {percent:.0f}%').format(percent=percentage))

    achievements = Achievement.objects.filter(course=lesson.course, is_active=True)
    for ach in achievements:
        levels = ach.levels.all()
        if levels:
            progress, _ = AchievementProgress.objects.get_or_create(user=request.user, achievement=ach)
            new_value = enrollment.lessons_completed
            if new_value > progress.current_value:
                progress.current_value = new_value
                progress.save()
                progress.check_and_update()

    return redirect('course_detail', slug=lesson.course.slug)


def course_leaderboard(request, slug):
    course = get_object_or_404(Course, slug=slug, status='published')
    enrollments = CourseEnrollment.objects.filter(course=course).select_related('user').order_by('-course_xp')
    leaderboard = []
    for idx, enrollment in enumerate(enrollments, start=1):
        leaderboard.append({
            'rank': idx,
            'username': enrollment.user.username,
            'lessons_completed': enrollment.lessons_completed,
            'course_xp': enrollment.course_xp,
        })
    return render(request, 'course_leaderboard.html', {'course': course, 'leaderboard': leaderboard})


@login_required
def league_table(request):
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    membership = UserLeagueMembership.objects.filter(user=request.user, week_start=week_start).first()
    if not membership:
        messages.info(request, _('Вы ещё не попали в лигу. Пройдите несколько уроков.'))
        return redirect('profile')
    league_instance = membership.league_instance
    all_members = UserLeagueMembership.objects.filter(league_instance=league_instance, week_start=week_start).order_by('-weekly_xp')
    for idx, m in enumerate(all_members, start=1):
        m.rank = idx
    user_rank = next((idx for idx, m in enumerate(all_members, start=1) if m.user == request.user), None)
    context = {
        'league_instance': league_instance,
        'members': all_members,
        'user_rank': user_rank,
        'week_start': week_start,
    }
    return render(request, 'league.html', context)


@login_required
def shop(request):
    items = ShopItem.objects.filter(is_active=True)
    user_inventory = UserInventory.objects.filter(user=request.user, used_at__isnull=True)
    return render(request, 'shop.html', {'items': items, 'inventory': user_inventory})


@login_required
def purchase_item(request, item_id):
    item = get_object_or_404(ShopItem, id=item_id, is_active=True)
    profile = request.user.profile
    if item.price_coins > 0 and profile.coins >= item.price_coins:
        profile.coins -= item.price_coins
        profile.save()
        expires_at = None
        if item.duration_minutes:
            expires_at = timezone.now() + timedelta(minutes=item.duration_minutes)
        UserInventory.objects.create(
            user=request.user,
            item=item,
            quantity=1,
            expires_at=expires_at
        )
        messages.success(request, _('Вы купили {item}!').format(item=item.tatar_name))
    elif item.price_tulips > 0 and profile.tulips >= item.price_tulips:
        profile.tulips -= item.price_tulips
        profile.save()
        UserInventory.objects.create(user=request.user, item=item, quantity=1)
        messages.success(request, _('Вы купили {item}!').format(item=item.tatar_name))
    else:
        messages.error(request, _('Недостаточно средств.'))
    return redirect('shop')


@login_required
def use_item(request, inventory_id):
    inv_item = get_object_or_404(UserInventory, id=inventory_id, user=request.user, used_at__isnull=True)
    item = inv_item.item
    if item.item_type == 'streak_protect':
        request.session['streak_protect_active'] = True
        messages.success(request, _('Тумар защиты активирован! При пропуске дня стрик не сбросится.'))
    elif item.item_type == 'xp_boost':
        request.session['xp_boost_until'] = (timezone.now() + timedelta(minutes=item.duration_minutes)).isoformat()
        messages.success(request, _('Курай-ускоритель активирован на {minutes} мин!').format(minutes=item.duration_minutes))
    else:
        messages.info(request, _('Этот предмет пока нельзя использовать.'))
    inv_item.used_at = timezone.now()
    inv_item.save()
    return redirect('shop')


@login_required
def achievements_list(request):
    achievements = Achievement.objects.prefetch_related('levels').all()
    user_progress = {ap.achievement_id: ap for ap in AchievementProgress.objects.filter(user=request.user)}
    context = {
        'achievements': achievements,
        'user_progress': user_progress,
    }
    return render(request, 'achievements.html', context)


def clan_leaderboard(request):
    course_slug = request.GET.get('course_id')
    if course_slug:
        course = get_object_or_404(Course, slug=course_slug, status='published')
    else:
        course = get_object_or_404(Course, slug='tatarskii-yazyk-s-nulya', status='published')
    enrollments = CourseEnrollment.objects.filter(course=course).select_related('user').order_by('-course_xp')
    leaderboard = []
    for idx, enrollment in enumerate(enrollments, start=1):
        leaderboard.append({
            'rank': idx,
            'username': enrollment.user.username,
            'lessons_completed': enrollment.lessons_completed,
            'course_xp': enrollment.course_xp,
        })
    return render(request, 'clan_leaderboard.html', {'course': course, 'leaderboard': leaderboard})


class CustomTestForm(forms.ModelForm):
    class Meta:
        model = CustomTest
        fields = ['title', 'subject', 'difficulty', 'course', 'reward_coins_per_question']


@login_required
def become_author(request):
    profile = request.user.profile
    if profile.lessons_completed >= 10 and not profile.is_author:
        profile.is_author = True
        profile.save()
        messages.success(request, _('Поздравляем! Вы стали автором. Теперь вы можете создавать тесты.'))
    elif profile.is_author:
        messages.info(request, _('Вы уже являетесь автором.'))
    else:
        messages.error(request, _('Необходимо пройти не менее 10 уроков. Вы прошли {count} из 10.').format(count=profile.lessons_completed))
    return redirect('profile')


@login_required
def create_test(request):
    profile = request.user.profile
    if not profile.is_author or profile.lessons_completed < 10:
        messages.error(request, _('Вы не можете создавать тесты. Нужно пройти минимум 10 уроков и получить статус автора.'))
        return redirect('home')
    if request.method == 'POST':
        test_form = CustomTestForm(request.POST)
        if test_form.is_valid():
            test = test_form.save(commit=False)
            test.author = request.user
            test.status = 'moderation'
            test.save()
            q_index = 0
            while True:
                text = request.POST.get(f'question_{q_index}_text')
                if not text:
                    break
                option1 = request.POST.get(f'question_{q_index}_option1')
                option2 = request.POST.get(f'question_{q_index}_option2')
                option3 = request.POST.get(f'question_{q_index}_option3', '')
                option4 = request.POST.get(f'question_{q_index}_option4', '')
                correct_option = int(request.POST.get(f'question_{q_index}_correct_option'))
                explanation = request.POST.get(f'question_{q_index}_explanation', '')
                CustomQuestion.objects.create(
                    test=test,
                    text=text,
                    option1=option1,
                    option2=option2,
                    option3=option3,
                    option4=option4,
                    correct_option=correct_option,
                    explanation=explanation
                )
                q_index += 1
            messages.success(request, _('Тест "{title}" отправлен на модерацию!').format(title=test.title))
            return redirect('my_tests')
    else:
        test_form = CustomTestForm()
    return render(request, 'create_test.html', {'test_form': test_form})


@login_required
def my_tests(request):
    tests = CustomTest.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'my_tests.html', {'tests': tests})


@login_required
def public_tests(request):
    tests = CustomTest.objects.filter(status='approved').order_by('-created_at')
    return render(request, 'public_tests.html', {'tests': tests})


@login_required
def take_custom_test(request, test_id):
    test = get_object_or_404(CustomTest, id=test_id, status='approved')
    questions = test.questions.all()
    if request.method == 'POST':
        score = 0
        for q in questions:
            ans = request.POST.get(f'question_{q.id}')
            if ans and int(ans) == q.correct_option:
                score += 1
        earned_coins = score * test.reward_coins_per_question
        CustomTestResult.objects.create(
            user=request.user,
            test=test,
            score=score,
            total_questions=questions.count(),
            earned_coins=earned_coins
        )
        profile = request.user.profile
        profile.coins += earned_coins
        profile.save()
        messages.success(request, _('Вы ответили правильно на {score} из {total} вопросов и заработали {coins} монет!').format(score=score, total=questions.count(), coins=earned_coins))
        return redirect('public_tests')
    return render(request, 'take_custom_test.html', {'test': test, 'questions': questions})


@login_required
def create_course(request):
    profile = request.user.profile
    if not profile.is_author:
        messages.error(request, _('Только авторы могут создавать курсы.'))
        return redirect('home')
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.is_official = False
            course.status = 'draft'
            course.author = request.user
            course.save()
            messages.success(request, _('Курс "{title}" создан и отправлен на модерацию!').format(title=course.title))
            return redirect('home')
    else:
        form = CourseForm()
    return render(request, 'create_course.html', {'form': form})


@login_required
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if course.author != request.user and not request.user.is_superuser:
        messages.error(request, _('Вы не можете редактировать этот курс.'))
        return redirect('course_detail', slug=course.slug)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, _('Курс успешно обновлён!'))
            return redirect('course_detail', slug=course.slug)
    else:
        form = CourseForm(instance=course)
    return render(request, 'edit_course.html', {'form': form, 'course': course})


@login_required
def add_lesson(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not request.user.profile.is_author or course.author != request.user:
        messages.error(request, _('Вы не можете добавлять уроки в этот курс.'))
        return redirect('home')
    user_tests = CustomTest.objects.filter(author=request.user, status='approved')
    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            last_order = Lesson.objects.filter(course=course).aggregate(models.Max('order'))['order__max'] or 0
            lesson.order = last_order + 1
            test_id = request.POST.get('test')
            if test_id:
                lesson.test_id = test_id
            lesson.save()
            for i in range(5):
                text = request.POST.get(f'question_{i}_text')
                if text:
                    option1 = request.POST.get(f'question_{i}_option1', '')
                    option2 = request.POST.get(f'question_{i}_option2', '')
                    option3 = request.POST.get(f'question_{i}_option3', '')
                    option4 = request.POST.get(f'question_{i}_option4', '')
                    correct = int(request.POST.get(f'question_{i}_correct_option', 1))
                    explanation = request.POST.get(f'question_{i}_explanation', '')
                    Question.objects.create(
                        lesson=lesson,
                        text=text,
                        option1=option1,
                        option2=option2,
                        option3=option3,
                        option4=option4,
                        correct_option=correct,
                        explanation=explanation
                    )
            messages.success(request, _('Урок "{title}" добавлен!').format(title=lesson.title))
            return redirect('course_detail', slug=course.slug)
    else:
        form = LessonForm()
    return render(request, 'add_lesson.html', {
        'form': form,
        'course': course,
        'user_tests': user_tests
    })


@login_required
def edit_custom_test(request, test_id):
    test = get_object_or_404(CustomTest, id=test_id)
    if test.author != request.user and not request.user.is_superuser:
        messages.error(request, _('Вы не можете редактировать этот тест.'))
        return redirect('my_tests')
    if request.method == 'POST':
        form = CustomTestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            test.questions.all().delete()
            q_index = 0
            while True:
                text = request.POST.get(f'question_{q_index}_text')
                if not text:
                    break
                option1 = request.POST.get(f'question_{q_index}_option1')
                option2 = request.POST.get(f'question_{q_index}_option2')
                option3 = request.POST.get(f'question_{q_index}_option3', '')
                option4 = request.POST.get(f'question_{q_index}_option4', '')
                correct_option = int(request.POST.get(f'question_{q_index}_correct_option'))
                explanation = request.POST.get(f'question_{q_index}_explanation', '')
                CustomQuestion.objects.create(
                    test=test,
                    text=text,
                    option1=option1,
                    option2=option2,
                    option3=option3,
                    option4=option4,
                    correct_option=correct_option,
                    explanation=explanation
                )
                q_index += 1
            messages.success(request, _('Тест "{title}" успешно обновлён!').format(title=test.title))
            return redirect('my_tests')
    else:
        form = CustomTestForm(instance=test)
    return render(request, 'edit_custom_test.html', {'form': form, 'test': test})


@login_required
def edit_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course
    if course.author != request.user and not request.user.is_superuser:
        messages.error(request, _('Вы не можете редактировать этот урок.'))
        return redirect('lesson_detail', course_slug=course.slug, order=lesson.order)
    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, _('Урок "{title}" успешно обновлён!').format(title=lesson.title))
            return redirect('lesson_detail', course_slug=course.slug, order=lesson.order)
    else:
        form = LessonForm(instance=lesson)
    return render(request, 'edit_lesson.html', {'form': form, 'lesson': lesson})


@login_required
def delete_custom_test(request, test_id):
    test = get_object_or_404(CustomTest, id=test_id)
    if test.author != request.user and not request.user.is_superuser:
        messages.error(request, _('Вы не можете удалить этот тест.'))
        return redirect('my_tests')
    test_title = test.title
    test.delete()
    messages.success(request, _('Тест "{title}" успешно удалён!').format(title=test_title))
    return redirect('my_tests')


@login_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if course.author != request.user and not request.user.is_superuser:
        messages.error(request, _('Вы не можете удалить этот курс.'))
        return redirect('course_detail', slug=course.slug)
    course_title = course.title
    course.delete()
    messages.success(request, _('Курс "{title}" успешно удалён!').format(title=course_title))
    return redirect('home')


@login_required
def delete_lesson_test(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course
    if course.author != request.user and not request.user.is_superuser:
        messages.error(request, _('Вы не можете удалить тест этого урока.'))
        return redirect('lesson_detail', course_slug=course.slug, order=lesson.order)
    lesson.questions.all().delete()
    messages.success(request, _('Тест урока "{title}" успешно удалён!').format(title=lesson.title))
    return redirect('lesson_detail', course_slug=course.slug, order=lesson.order)


@login_required
def attach_test_to_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if course.author != request.user and not request.user.is_superuser:
        messages.error(request, _('Вы не можете изменять тесты этого курса.'))
        return redirect('course_detail', slug=course.slug)
    user_tests = CustomTest.objects.filter(author=request.user, status='approved').exclude(attached_courses=course)
    if request.method == 'POST':
        test_id = request.POST.get('test_id')
        if test_id:
            test = get_object_or_404(CustomTest, id=test_id)
            course.additional_tests.add(test)
            messages.success(request, _('Тест "{title}" привязан к курсу!').format(title=test.title))
        return redirect('course_detail', slug=course.slug)
    return render(request, 'attach_test_to_course.html', {'course': course, 'user_tests': user_tests})


@login_required
def add_course_review(request, slug):
    course = get_object_or_404(Course, slug=slug, status='published')
    has_completed = CourseEnrollment.objects.filter(user=request.user, course=course).exists()
    if not has_completed:
        messages.error(request, _('Вы можете оставить отзыв только после изучения курса.'))
        return redirect('course_detail', slug=course.slug)
    existing_review = CourseReview.objects.filter(user=request.user, course=course).first()
    if existing_review:
        messages.error(request, _('Вы уже оставили отзыв на этот курс.'))
        return redirect('course_detail', slug=course.slug)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        if not rating or not comment:
            messages.error(request, _('Пожалуйста, заполните все поля.'))
            return redirect('add_course_review', slug=course.slug)
        CourseReview.objects.create(
            user=request.user,
            course=course,
            rating=int(rating),
            comment=comment,
            is_approved=True
        )
        messages.success(request, _('Спасибо за отзыв! Он появится после проверки модератором.'))
        return redirect('course_detail', slug=course.slug)
    return render(request, 'add_course_review.html', {'course': course})


def community_list(request):
    communities = Community.objects.filter(is_active=True)
    query = request.GET.get('q')
    if query:
        communities = communities.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(tags__icontains=query))
    sort = request.GET.get('sort', 'members')
    if sort == 'members':
        communities = communities.order_by('-member_count')
    elif sort == 'new':
        communities = communities.order_by('-created_at')
    else:
        communities = communities.order_by('order', 'name')
    return render(request, 'community_list.html', {'communities': communities})


@login_required
def community_create(request):
    if request.method == 'POST':
        form = CommunityForm(request.POST)
        if form.is_valid():
            community = form.save(commit=False)
            community.owner = request.user
            community.is_active = True
            community.is_approved = True

            base_slug = slugify(community.name)
            if not base_slug:
                base_slug = "community"
            slug = base_slug
            counter = 1
            while Community.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            community.slug = slug

            community.save()
            form.save_m2m()
            CommunityMembership.objects.create(community=community, user=request.user, role='admin')
            community.member_count = 1
            community.save()

            messages.success(request, _('Сообщество "{name}" успешно создано!').format(name=community.name))
            return redirect('community_detail', slug=community.slug)
    else:
        form = CommunityForm()
    return render(request, 'community_create.html', {'form': form})


def community_detail(request, slug):
    community = get_object_or_404(Community, slug=slug, is_active=True)
    user = request.user
    membership = None
    if user.is_authenticated:
        membership = CommunityMembership.objects.filter(community=community, user=user).first()
    if community.is_private and not membership and not user.is_superuser:
        if request.method == 'POST' and request.POST.get('password') == community.join_password:
            CommunityMembership.objects.create(community=community, user=user, role='member')
            community.member_count += 1
            community.save()
            messages.success(request, _('Вы вступили в сообщество "{name}"!').format(name=community.name))
            return redirect('community_detail', slug=community.slug)
        return render(request, 'community_private.html', {'community': community})
    posts = community.posts.select_related('author').order_by('-is_pinned', '-created_at')
    external_links = community.external_links.filter(is_active=True).order_by('order')
    week_ago = timezone.now() - timedelta(days=7)
    top_members = User.objects.filter(
        community_posts__community=community,
        community_posts__created_at__gte=week_ago
    ).annotate(activity_count=Count('community_posts')).order_by('-activity_count')[:5]
    context = {
        'community': community,
        'posts': posts,
        'external_links': external_links,
        'top_members': top_members,
        'membership': membership,
    }
    return render(request, 'community_detail.html', context)


@login_required
def community_join(request, slug):
    community = get_object_or_404(Community, slug=slug, is_active=True)
    membership = CommunityMembership.objects.filter(community=community, user=request.user).first()
    if not membership:
        CommunityMembership.objects.create(community=community, user=request.user, role='member')
        community.member_count += 1
        community.save()
        messages.success(request, _('Вы вступили в сообщество "{name}"!').format(name=community.name))
    else:
        messages.info(request, _('Вы уже состоите в этом сообществе.'))
    return redirect('community_detail', slug=community.slug)


@login_required
def community_leave(request, slug):
    community = get_object_or_404(Community, slug=slug)
    membership = CommunityMembership.objects.filter(community=community, user=request.user).first()
    if membership and membership.role != 'admin' and community.owner != request.user:
        membership.delete()
        community.member_count -= 1
        community.save()
        messages.success(request, _('Вы покинули сообщество "{name}".').format(name=community.name))
    else:
        messages.error(request, _('Вы не можете покинуть сообщество, так как являетесь его владельцем или администратором.'))
    return redirect('community_detail', slug=community.slug)


@login_required
def community_add_post(request, slug):
    community = get_object_or_404(Community, slug=slug, is_active=True)
    membership = CommunityMembership.objects.filter(community=community, user=request.user).first()
    if not membership:
        messages.error(request, _('Вы должны состоять в сообществе, чтобы создавать посты.'))
        return redirect('community_detail', slug=slug)
    if request.method == 'POST':
        form = CommunityPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.community = community
            post.author = request.user
            post.save()
            messages.success(request, _('Ваш пост опубликован!'))
            return redirect('community_detail', slug=slug)
    else:
        form = CommunityPostForm()
    return render(request, 'community_add_post.html', {'form': form, 'community': community})


@login_required
def community_edit_post(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    community = post.community
    if not (request.user == post.author or community.user_can_manage(request.user)):
        messages.error(request, _('У вас нет прав на редактирование этого поста.'))
        return redirect('community_detail', slug=community.slug)
    if request.method == 'POST':
        form = CommunityPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, _('Пост обновлён.'))
            return redirect('community_detail', slug=community.slug)
    else:
        form = CommunityPostForm(instance=post)
    return render(request, 'community_edit_post.html', {'form': form, 'post': post, 'community': community})


@login_required
def community_delete_post(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    community = post.community
    if not (request.user == post.author or community.user_can_manage(request.user)):
        messages.error(request, _('Недостаточно прав.'))
        return redirect('community_detail', slug=community.slug)
    post.delete()
    messages.success(request, _('Пост удалён.'))
    return redirect('community_detail', slug=community.slug)


@login_required
def community_like_post(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect('community_detail', slug=post.community.slug)


@login_required
def community_add_comment(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    community = post.community
    membership = CommunityMembership.objects.filter(community=community, user=request.user).first()
    if not membership:
        messages.error(request, _('Вы должны быть участником сообщества, чтобы комментировать.'))
        return redirect('community_detail', slug=community.slug)
    if request.method == 'POST':
        form = CommunityCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            post.comments_count += 1
            post.save()
            messages.success(request, _('Комментарий добавлен.'))
    return redirect('community_detail', slug=community.slug)


@login_required
def community_delete_comment(request, comment_id):
    comment = get_object_or_404(CommunityComment, id=comment_id)
    community = comment.post.community
    if not (request.user == comment.author or community.user_can_manage(request.user)):
        messages.error(request, _('Недостаточно прав.'))
        return redirect('community_detail', slug=community.slug)
    comment.post.comments_count -= 1
    comment.post.save()
    comment.delete()
    messages.success(request, _('Комментарий удалён.'))
    return redirect('community_detail', slug=community.slug)


@login_required
def community_add_link(request, slug):
    community = get_object_or_404(Community, slug=slug, is_active=True)
    if not community.user_can_manage(request.user):
        messages.error(request, _('У вас нет прав на управление ссылками.'))
        return redirect('community_detail', slug=slug)
    if request.method == 'POST':
        form = CommunityExternalLinkForm(request.POST)
        if form.is_valid():
            link = form.save(commit=False)
            link.community = community
            link.save()
            messages.success(request, _('Ссылка добавлена.'))
            return redirect('community_detail', slug=slug)
    else:
        form = CommunityExternalLinkForm()
    return render(request, 'community_add_link.html', {'form': form, 'community': community})


@login_required
def community_edit_link(request, link_id):
    link = get_object_or_404(CommunityExternalLink, id=link_id)
    community = link.community
    if not community.user_can_manage(request.user):
        messages.error(request, _('Недостаточно прав.'))
        return redirect('community_detail', slug=community.slug)
    if request.method == 'POST':
        form = CommunityExternalLinkForm(request.POST, instance=link)
        if form.is_valid():
            form.save()
            messages.success(request, _('Ссылка обновлена.'))
            return redirect('community_detail', slug=community.slug)
    else:
        form = CommunityExternalLinkForm(instance=link)
    return render(request, 'community_edit_link.html', {'form': form, 'link': link, 'community': community})


@login_required
def community_delete_link(request, link_id):
    link = get_object_or_404(CommunityExternalLink, id=link_id)
    community = link.community
    if not community.user_can_manage(request.user):
        messages.error(request, _('Недостаточно прав.'))
        return redirect('community_detail', slug=community.slug)
    link.delete()
    messages.success(request, _('Ссылка удалена.'))
    return redirect('community_detail', slug=community.slug)


@login_required
def community_manage(request, slug):
    community = get_object_or_404(Community, slug=slug, is_active=True)
    if not community.user_can_manage(request.user):
        messages.error(request, _('Доступ запрещён.'))
        return redirect('community_detail', slug=slug)
    members = CommunityMembership.objects.filter(community=community).select_related('user').order_by('-joined_at')
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        action = request.POST.get('action')
        membership = CommunityMembership.objects.filter(community=community, user_id=user_id).first()
        if membership:
            if action == 'ban':
                membership.is_banned = True
                membership.save()
                messages.success(request, _('Пользователь забанен.'))
            elif action == 'unban':
                membership.is_banned = False
                membership.save()
                messages.success(request, _('Бан снят.'))
            elif new_role in dict(CommunityMembership.ROLE_CHOICES):
                membership.role = new_role
                membership.save()
                messages.success(request, _('Роль изменена.'))
        return redirect('community_manage', slug=slug)
    return render(request, 'community_manage.html', {'community': community, 'members': members})


def community_search(request):
    query = request.GET.get('q', '')
    communities = Community.objects.filter(is_active=True)
    if query:
        communities = communities.filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(tags__icontains=query))
    return render(request, 'community_search_results.html', {'communities': communities, 'query': query})


@login_required
def community_chat(request, slug):
    community = get_object_or_404(Community, slug=slug, is_active=True, has_chat=True)
    membership = CommunityMembership.objects.filter(community=community, user=request.user).first()
    if not membership and not request.user.is_superuser:
        messages.error(request, _('Вы должны состоять в сообществе, чтобы пользоваться чатом.'))
        return redirect('community_detail', slug=slug)
    room, _ = CommunityChatRoom.objects.get_or_create(community=community)
    messages_list = room.messages.all().select_related('user')[:50]
    context = {
        'community': community,
        'messages': messages_list,
        'room_name': community.slug,
    }
    return render(request, 'community_chat.html', context)


@login_required
def user_profile(request, username):
    target_user = get_object_or_404(User, username=username)
    profile = target_user.profile

    are_friends = Friendship.are_friends(request.user, target_user)
    pending_sent = Friendship.objects.filter(
        from_user=request.user, to_user=target_user, status='pending'
    ).exists()
    pending_received_obj = Friendship.objects.filter(
        from_user=target_user, to_user=request.user, status='pending'
    ).first()
    pending_received_id = pending_received_obj.id if pending_received_obj else None

    achievements_progress = target_user.achievements_progress.select_related('achievement').all()
    enrolled_courses = CourseEnrollment.objects.filter(user=target_user).select_related('course')

    context = {
        'target_user': target_user,
        'profile': profile,
        'are_friends': are_friends,
        'pending_sent': pending_sent,
        'pending_received': pending_received_obj,
        'pending_received_id': pending_received_id,
        'achievements_progress': achievements_progress,
        'enrolled_courses': enrolled_courses,
    }
    return render(request, 'user_profile.html', context)


@login_required
def add_friend(request, username):
    target_user = get_object_or_404(User, username=username)

    if request.user == target_user:
        messages.error(request, _('Нельзя добавить самого себя в друзья.'))
        return redirect('user_profile', username=username)

    incoming = Friendship.objects.filter(
        from_user=target_user, to_user=request.user, status='pending'
    ).first()

    if incoming:
        incoming.accept()
        from .services.achievement_service import AchievementService
        from django.db.models import Q
        friends_count = Friendship.objects.filter(
            Q(from_user=request.user, status='accepted') |
            Q(to_user=request.user, status='accepted')
        ).count()
        AchievementService.check_friends_achievement(request.user, friends_count)
        messages.success(request, _('Вы стали друзьями с {username}!').format(username=target_user.username))
        return redirect('user_profile', username=username)

    existing = Friendship.objects.filter(
        from_user=request.user, to_user=target_user, status='pending'
    ).first()

    if existing:
        messages.info(request, _('Заявка уже отправлена.'))
        return redirect('user_profile', username=username)

    Friendship.objects.create(from_user=request.user, to_user=target_user, status='pending')
    messages.success(request, _('Заявка в друзья отправлена пользователю {username}.').format(username=target_user.username))
    return redirect('user_profile', username=username)


@login_required
def accept_friend(request, friendship_id):
    friendship = get_object_or_404(Friendship, id=friendship_id, to_user=request.user, status='pending')
    friendship.accept()
    messages.success(request, _('Вы приняли заявку от {username}.').format(username=friendship.from_user.username))
    return redirect('profile')


@login_required
def remove_friend(request, username):
    target_user = get_object_or_404(User, username=username)

    friendship = Friendship.objects.filter(
        Q(from_user=request.user, to_user=target_user) |
        Q(from_user=target_user, to_user=request.user)
    ).first()

    if friendship:
        friendship.delete()
        messages.success(request, _('Вы удалили {username} из друзей.').format(username=target_user.username))
    else:
        messages.error(request, _('Дружба не найдена.'))

    return redirect('user_profile', username=username)


@login_required
def my_friends(request):
    friends_users = User.objects.filter(
        Q(friend_requests_sent__to_user=request.user, friend_requests_sent__status='accepted') |
        Q(friend_requests_received__from_user=request.user, friend_requests_received__status='accepted')
    ).distinct()

    incoming_requests = Friendship.objects.filter(to_user=request.user, status='pending')
    outgoing_requests = Friendship.objects.filter(from_user=request.user, status='pending')

    context = {
        'friends': friends_users,
        'incoming_requests': incoming_requests,
        'outgoing_requests': outgoing_requests,
    }
    return render(request, 'my_friends.html', context)