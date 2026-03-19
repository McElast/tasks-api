"""Форма задачи."""

from typing import Any

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

from ..models import Task
from ..validation import normalize_text

UserModel = get_user_model()


class TaskForm(forms.ModelForm):  # type: ignore[type-arg]
    """Форма создания и редактирования задачи."""

    class Meta:
        """Мета-настройки формы задачи."""

        model = Task
        fields = ['title', 'description', 'status', 'assignee']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args: Any, current_user: User, **kwargs: Any) -> None:
        """Настраивает форму с учётом текущего пользователя."""
        super().__init__(*args, **kwargs)
        assignee_field = self.fields['assignee']
        if not isinstance(assignee_field, forms.ModelChoiceField):
            raise TypeError('TaskForm expects `assignee` to be a ModelChoiceField.')
        assignee_field.queryset = UserModel.objects.order_by('username')
        if self.instance.pk and self.instance.author_id != current_user.pk:
            assignee_field.disabled = True
            assignee_field.help_text = 'Только автор задачи может менять исполнителя.'
        self.fields['title'].widget.attrs.update({'placeholder': 'Например: Подготовить отчёт по спринту'})
        self.fields['description'].widget.attrs.update({'placeholder': 'Опишите задачу подробнее'})

    def clean_title(self) -> str:
        """Проверяет корректность заголовка задачи."""
        title = normalize_text(self.cleaned_data['title'])
        if not title:
            raise forms.ValidationError('Заголовок задачи не может быть пустым.')
        return title
