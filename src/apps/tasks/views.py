"""Полностью асинхронные HTML-представления приложения задач."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views import View

from .selectors import filter_tasks_for_user, resolve_task_filter
from .mixins import UserTaskAccessMixin
from .services import complete_task, create_comment, create_task, delete_task, reopen_task, update_task
from .view_helpers import (
    build_comment_form,
    build_task_form,
    get_async_request_user,
    get_user_task_or_404,
    run_sync,
    task_form_context,
    task_form_payload,
)


@login_required
async def task_list_view(request: HttpRequest) -> HttpResponse:
    """Отображает список задач текущего пользователя."""
    user = await get_async_request_user(request)
    filter_name = resolve_task_filter(request.GET.get('filter'))
    tasks = await run_sync(lambda: list(filter_tasks_for_user(user=user, filter_name=filter_name)))
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
    user = await get_async_request_user(request)
    task = await run_sync(get_user_task_or_404, user=user, task_id=task_id)
    return TemplateResponse(
        request,
        'tasks/task_detail.html',
        {
            'task': task,
            'comment_form': await run_sync(build_comment_form),
            'can_delete': task.author_id == user.pk,
            'can_change_assignee': task.author_id == user.pk,
        },
    )


class TaskCreateView(UserTaskAccessMixin, View):
    """Асинхронно создаёт задачу через HTML-форму."""

    async def get(self, request: HttpRequest) -> HttpResponse:
        """Отображает пустую форму создания задачи."""
        form = await run_sync(build_task_form, current_user=await self.get_request_user(request))
        return TemplateResponse(
            request,
            'tasks/task_form.html',
            task_form_context(form=form, page_title='Новая задача', submit_label='Создать задачу'),
        )

    async def post(self, request: HttpRequest) -> HttpResponse:
        """Создаёт задачу после валидации формы."""
        user = await self.get_request_user(request)
        form = await run_sync(build_task_form, current_user=user, data=request.POST)
        if await run_sync(form.is_valid):
            task = await run_sync(
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
            task_form_context(form=form, page_title='Новая задача', submit_label='Создать задачу'),
        )


class TaskUpdateView(UserTaskAccessMixin, View):
    """Асинхронно редактирует задачу через HTML-форму."""

    async def get(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Отображает форму редактирования задачи."""
        user = await self.get_request_user(request)
        task = await self.get_user_task(request, task_id)
        form = await run_sync(build_task_form, current_user=user, instance=task)
        return TemplateResponse(
            request,
            'tasks/task_form.html',
            task_form_context(form=form, page_title='Редактирование задачи', submit_label='Сохранить изменения'),
        )

    async def post(self, request: HttpRequest, task_id: int) -> HttpResponse:
        """Обновляет задачу после валидации формы."""
        user = await self.get_request_user(request)
        task = await self.get_user_task(request, task_id)
        form = await run_sync(build_task_form, current_user=user, data=request.POST, instance=task)
        if await run_sync(form.is_valid):
            updated_task = await run_sync(
                update_task,
                actor=user,
                task=task,
                data=await run_sync(task_form_payload, form),
            )
            messages.success(request, 'Задача обновлена.')
            return redirect('task-detail', task_id=updated_task.pk)
        return TemplateResponse(
            request,
            'tasks/task_form.html',
            task_form_context(form=form, page_title='Редактирование задачи', submit_label='Сохранить изменения'),
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
        await run_sync(delete_task, actor=user, task=task)
        messages.success(request, 'Задача удалена.')
        return redirect('task-list')


class TaskCommentCreateView(UserTaskAccessMixin, View):
    """Асинхронно создаёт комментарий к задаче из HTML-интерфейса."""

    async def post(self, request: HttpRequest, task_id: int) -> HttpResponseRedirect:
        """Создаёт комментарий и возвращает пользователя на страницу задачи."""
        user = await self.get_request_user(request)
        task = await self.get_user_task(request, task_id)
        form = await run_sync(build_comment_form, data=request.POST)
        if await run_sync(form.is_valid):
            await run_sync(create_comment, actor=user, task=task, text=form.cleaned_data['text'])
            messages.success(request, 'Комментарий добавлен.')
        else:
            messages.error(request, 'Не удалось добавить комментарий.')
        return redirect('task-detail', task_id=task_id)


@login_required
async def complete_task_view(request: HttpRequest, task_id: int) -> HttpResponseRedirect:
    """Завершает задачу и возвращает пользователя на её карточку."""
    if request.method != 'POST':
        raise PermissionDenied('Действие доступно только через POST.')
    user = await get_async_request_user(request)
    task = await run_sync(get_user_task_or_404, user=user, task_id=task_id)
    await run_sync(complete_task, actor=user, task=task)
    messages.success(request, 'Задача завершена.')
    return UserTaskAccessMixin.redirect_to_task(task_id)


@login_required
async def reopen_task_view(request: HttpRequest, task_id: int) -> HttpResponseRedirect:
    """Повторно открывает задачу и возвращает пользователя на её карточку."""
    if request.method != 'POST':
        raise PermissionDenied('Действие доступно только через POST.')
    user = await get_async_request_user(request)
    task = await run_sync(get_user_task_or_404, user=user, task_id=task_id)
    await run_sync(reopen_task, actor=user, task=task)
    messages.success(request, 'Задача снова активна.')
    return UserTaskAccessMixin.redirect_to_task(task_id)
