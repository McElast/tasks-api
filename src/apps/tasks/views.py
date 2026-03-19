"""Полностью асинхронные HTML-представления приложения задач."""

from collections.abc import Callable
from typing import Any

from asgiref.sync import sync_to_async
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views import View

from .forms import CommentForm, TaskForm
from .models import Task
from .selectors import TaskFilter, filter_tasks_for_user
from .services import (
    TaskUpdateData,
    complete_task,
    create_comment,
    create_task,
    delete_task,
    reopen_task,
    update_task,
)


def _resolve_filter_name(raw_filter: str | None) -> TaskFilter:
    """Нормализует имя фильтра задач для HTML-списка."""
    if raw_filter == 'mine':
        return 'mine'
    if raw_filter == 'assigned':
        return 'assigned'
    if raw_filter == 'completed':
        return 'completed'
    if raw_filter == 'active':
        return 'active'
    return 'all'


def _build_task_form(*, current_user: User, data: Any = None, instance: Task | None = None) -> TaskForm:
    """Создаёт форму задачи в синхронном контексте для безопасного вызова из async view."""
    return TaskForm(data=data, instance=instance, current_user=current_user)


def _build_comment_form(*, data: Any = None) -> CommentForm:
    """Создаёт форму комментария в синхронном контексте."""
    return CommentForm(data=data)


def _get_request_user(request: HttpRequest) -> User:
    """Возвращает типизированного пользователя запроса."""
    user = request.user
    if not isinstance(user, User):
        raise TypeError('Authenticated HTML request must contain django.contrib.auth User.')
    return user


async def _get_async_request_user(request: HttpRequest) -> User:
    """Возвращает типизированного пользователя из async request.auser()."""
    user = await request.auser()
    if not isinstance(user, User):
        raise TypeError('Authenticated HTML request must contain django.contrib.auth User.')
    return user


async def _run_sync[T](func: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Выполняет sync-функцию из async HTML view."""
    return await sync_to_async(func)(*args, **kwargs)


def _task_form_context(*, form: TaskForm, page_title: str, submit_label: str) -> dict[str, Any]:
    """Собирает стандартный контекст страницы формы задачи."""
    return {
        'form': form,
        'page_title': page_title,
        'submit_label': submit_label,
    }


def _get_user_task_or_404(*, user: User, task_id: int) -> Task:
    """Возвращает задачу пользователя или поднимает 404."""
    queryset = filter_tasks_for_user(user=user, filter_name='all')
    return get_object_or_404(queryset, pk=task_id)


def _task_form_payload(form: TaskForm) -> TaskUpdateData:
    """Собирает payload обновления задачи из валидной формы."""
    return TaskUpdateData(
        title=form.cleaned_data['title'],
        description=form.cleaned_data['description'],
        status=form.cleaned_data['status'],
        assignee=form.cleaned_data['assignee'],
    )


@login_required
async def task_list_view(request: HttpRequest) -> HttpResponse:
    """Отображает список задач текущего пользователя."""
    user = await _get_async_request_user(request)
    filter_name = _resolve_filter_name(request.GET.get('filter'))
    tasks = await _run_sync(lambda: list(filter_tasks_for_user(user=user, filter_name=filter_name)))
    return TemplateResponse(
        request,
        'tasks/task_list.html',
        {
            'tasks': tasks,
            'current_filter': filter_name,
        },
    )


@login_required
async def task_detail_view(request: HttpRequest, task_id: int) -> HttpResponse:
    """Отображает детальную страницу задачи с комментариями."""
    user = await _get_async_request_user(request)
    task = await _run_sync(_get_user_task_or_404, user=user, task_id=task_id)
    return TemplateResponse(
        request,
        'tasks/task_detail.html',
        {
            'task': task,
            'comment_form': await _run_sync(_build_comment_form),
            'can_delete': task.author_id == user.pk,
            'can_change_assignee': task.author_id == user.pk,
        },
    )


class UserTaskAccessMixin(LoginRequiredMixin):
    """Общие async-утилиты для HTML views задач."""

    @staticmethod
    async def get_request_user(request: HttpRequest) -> User:
        """Возвращает типизированного пользователя запроса."""
        return _get_request_user(request)

    async def get_user_task(self, request: HttpRequest, task_id: int) -> Task:
        """Возвращает задачу, доступную текущему пользователю."""
        return await _run_sync(_get_user_task_or_404, user=await self.get_request_user(request), task_id=task_id)

    async def get_deletable_task(self, request: HttpRequest, task_id: int) -> Task:
        """Возвращает задачу, которую текущий пользователь может удалить."""
        user = await self.get_request_user(request)
        task = await self.get_user_task(request, task_id)
        if task.author_id != user.pk:
            raise PermissionDenied('Удалять задачу может только её автор.')
        return task

    @staticmethod
    def redirect_to_task(task_id: int) -> HttpResponseRedirect:
        """Перенаправляет на карточку задачи."""
        return HttpResponseRedirect(reverse('task-detail', kwargs={'task_id': task_id}))


class TaskCreateView(UserTaskAccessMixin, View):
    """Асинхронно создаёт задачу через HTML-форму."""

    async def get(self, request: HttpRequest) -> HttpResponse:
        """Отображает пустую форму создания задачи."""
        form = await _run_sync(_build_task_form, current_user=await self.get_request_user(request))
        return TemplateResponse(
            request,
            'tasks/task_form.html',
            _task_form_context(form=form, page_title='Новая задача', submit_label='Создать задачу'),
        )

    async def post(self, request: HttpRequest) -> HttpResponse:
        """Создаёт задачу после валидации формы."""
        user = await self.get_request_user(request)
        form = await _run_sync(_build_task_form, current_user=user, data=request.POST)
        if await _run_sync(form.is_valid):
            task = await _run_sync(
                create_task,
                actor=user,
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                assignee=form.cleaned_data['assignee'],
                status=form.cleaned_data['status'],
            )
            messages.success(request, 'Задача создана.')
            return redirect('task-detail', task_id=task.pk)
        return TemplateResponse(
            request,
            'tasks/task_form.html',
            _task_form_context(form=form, page_title='Новая задача', submit_label='Создать задачу'),
        )


class TaskUpdateView(UserTaskAccessMixin, View):
    """Асинхронно редактирует задачу через HTML-форму."""

    async def get(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Отображает форму редактирования задачи."""
        user = await self.get_request_user(request)
        task = await self.get_user_task(request, task_id)
        form = await _run_sync(_build_task_form, current_user=user, instance=task)
        return TemplateResponse(
            request,
            'tasks/task_form.html',
            _task_form_context(form=form, page_title='Редактирование задачи', submit_label='Сохранить изменения'),
        )

    async def post(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Обновляет задачу после валидации формы."""
        user = await self.get_request_user(request)
        task = await self.get_user_task(request, task_id)
        form = await _run_sync(_build_task_form, current_user=user, data=request.POST, instance=task)
        if await _run_sync(form.is_valid):
            updated_task = await _run_sync(
                update_task,
                actor=user,
                task=task,
                data=await _run_sync(_task_form_payload, form),
            )
            messages.success(request, 'Задача обновлена.')
            return redirect('task-detail', task_id=updated_task.pk)
        return TemplateResponse(
            request,
            'tasks/task_form.html',
            _task_form_context(form=form, page_title='Редактирование задачи', submit_label='Сохранить изменения'),
        )


class TaskDeleteView(UserTaskAccessMixin, View):
    """Асинхронно удаляет задачу через HTML-интерфейс."""

    async def get(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Показывает страницу подтверждения удаления."""
        task = await self.get_deletable_task(request, task_id)
        return TemplateResponse(request, 'tasks/task_confirm_delete.html', {'object': task})

    async def post(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Удаляет задачу, если действие выполняет её автор."""
        user = await self.get_request_user(request)
        task = await self.get_deletable_task(request, task_id)
        await _run_sync(delete_task, actor=user, task=task)
        messages.success(request, 'Задача удалена.')
        return redirect('task-list')


class TaskCommentCreateView(UserTaskAccessMixin, View):
    """Асинхронно создаёт комментарий к задаче из HTML-интерфейса."""

    async def post(self, request: HttpRequest, task_id: int) -> HttpResponseRedirect:
        """Создаёт комментарий и возвращает пользователя на страницу задачи."""
        user = await self.get_request_user(request)
        task = await self.get_user_task(request, task_id)
        form = await _run_sync(_build_comment_form, data=request.POST)
        if await _run_sync(form.is_valid):
            await _run_sync(create_comment, actor=user, task=task, text=form.cleaned_data['text'])
            messages.success(request, 'Комментарий добавлен.')
        else:
            messages.error(request, 'Не удалось добавить комментарий.')
        return redirect('task-detail', task_id=task_id)


@login_required
async def complete_task_view(request: HttpRequest, task_id: int) -> HttpResponseRedirect:
    """Завершает задачу и возвращает пользователя на её карточку."""
    if request.method != 'POST':
        raise PermissionDenied('Действие доступно только через POST.')
    user = await _get_async_request_user(request)
    task = await _run_sync(_get_user_task_or_404, user=user, task_id=task_id)
    await _run_sync(complete_task, actor=user, task=task)
    messages.success(request, 'Задача завершена.')
    return UserTaskAccessMixin.redirect_to_task(task_id)


@login_required
async def reopen_task_view(request: HttpRequest, task_id: int) -> HttpResponseRedirect:
    """Повторно открывает задачу и возвращает пользователя на её карточку."""
    if request.method != 'POST':
        raise PermissionDenied('Действие доступно только через POST.')
    user = await _get_async_request_user(request)
    task = await _run_sync(_get_user_task_or_404, user=user, task_id=task_id)
    await _run_sync(reopen_task, actor=user, task=task)
    messages.success(request, 'Задача снова активна.')
    return UserTaskAccessMixin.redirect_to_task(task_id)
