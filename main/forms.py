from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Course, Lesson, Community, CommunityPost, CommunityComment, CommunityExternalLink, CourseReview


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'short_description', 'level', 'price', 'is_free', 'icon_class',
                  'duration_weeks', 'lessons_count']


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'section', 'content', 'video_url', 'duration_minutes', 'is_free_preview', 'test']


class DragonRatingWidget(forms.RadioSelect):
    template_name = 'dragon_rating_widget.html'


class CourseReviewForm(forms.ModelForm):
    class Meta:
        model = CourseReview
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': _('Поделитесь впечатлениями о курсе...')}),
        }


class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ['name', 'description', 'icon_class', 'cover_image', 'is_private', 'join_password', 'rules', 'tags', 'courses']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'rules': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': _('Правила сообщества...')}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('например: кулинария, рецепты')}),
            'courses': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['courses'].queryset = Course.objects.filter(status='published')
        self.fields['courses'].required = False


class CommunityPostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Заголовок поста')}),
            'content': forms.Textarea(attrs={'rows': 10, 'class': 'form-control', 'placeholder': _('Текст поста...')}),
        }


class CommunityCommentForm(forms.ModelForm):
    class Meta:
        model = CommunityComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': _('Ваш комментарий...')}),
        }


class CommunityExternalLinkForm(forms.ModelForm):
    class Meta:
        model = CommunityExternalLink
        fields = ['link_type', 'url', 'title', 'icon_class', 'order']
        widgets = {
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://vk.com/...'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Название (опционально)')}),
            'icon_class': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fab fa-vk'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_url(self):
        url = self.cleaned_data['url']
        link_type = self.cleaned_data.get('link_type')
        if link_type in ['vkontakte', 'vkontakte_video']:
            if not (url.startswith('https://vk.com/') or url.startswith('https://m.vk.com/')):
                raise forms.ValidationError(_('Ссылка должна вести на домен vk.com'))
        elif link_type == 'rutube':
            if not url.startswith('https://rutube.ru/'):
                raise forms.ValidationError(_('Ссылка должна вести на домен rutube.ru'))
        return url