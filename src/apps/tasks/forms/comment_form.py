"""Форма комментария."""

from django import forms

from ..models import Comment
from ..validation import normalize_text


class CommentForm(forms.ModelForm):  # type: ignore[type-arg]
    """Форма добавления комментария."""

    class Meta:
        """Мета-настройки формы комментария."""

        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Напишите комментарий'}),
        }

    def clean_text(self) -> str:
        """Проверяет, что комментарий не пустой."""
        text = normalize_text(self.cleaned_data['text'])
        if not text:
            raise forms.ValidationError('Текст комментария не может быть пустым.')
        return text
