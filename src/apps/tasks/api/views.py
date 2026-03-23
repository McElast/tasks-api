"""Полностью асинхронные REST API-представления для задач и пользователей."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from ..selectors import filter_tasks_for_user, resolve_task_filter
from ..services import complete_task, create_comment, reopen_task
from .async_api_view import AsyncAPIView as APIView
from .mixins import TaskObjectPermissionMixin
from .permissions import TaskAccessPermission
from .serializers import CommentSerializer, TaskSerializer, UserSerializer
from .view_helpers import (
    COMMENT_CREATE_RESPONSES,
    COMMENT_LIST_RESPONSES,
    TASK_DELETE_RESPONSES,
    TASK_DETAIL_RESPONSES,
    build_comment_serializer,
    build_task_serializer,
    get_request_user,
    run_sync,
    serialize_comment,
    serialize_comments,
    serialize_task,
    serialize_tasks,
    serialize_user,
)


class UserMeAPIView(APIView):
    """Возвращает данные текущего пользователя."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['users'],
        summary='Получить профиль текущего пользователя',
        responses={status.HTTP_200_OK: UserSerializer},
    )
    async def get(self, request: Request) -> Response:
        """Сериализует текущего пользователя и возвращает ответ API."""
        return Response(await run_sync(serialize_user, get_request_user(request)))


class TaskListCreateAPIView(APIView):
    """Асинхронно обрабатывает список задач и создание новой задачи."""

    permission_classes = [TaskAccessPermission]

    @extend_schema(
        tags=['tasks'],
        summary='Получить список доступных задач',
        responses={status.HTTP_200_OK: TaskSerializer(many=True)},
    )
    async def get(self, request: Request) -> Response:
        """Возвращает список задач, доступных текущему пользователю."""
        filter_name = resolve_task_filter(request.query_params.get('filter'))
        tasks = await run_sync(lambda: list(filter_tasks_for_user(user=request.user, filter_name=filter_name)))
        return Response(await run_sync(serialize_tasks, tasks, request=request))

    @extend_schema(
        tags=['tasks'],
        summary='Создать задачу',
        request=TaskSerializer,
        responses={status.HTTP_201_CREATED: TaskSerializer},
    )
    async def post(self, request: Request) -> Response:
        """Создаёт задачу через сериализатор и сервисный слой."""
        serializer = await run_sync(build_task_serializer, request=request, data=request.data)
        await run_sync(serializer.is_valid, raise_exception=True)
        task = await run_sync(serializer.save)
        return Response(await run_sync(serialize_task, task, request=request), status=status.HTTP_201_CREATED)


class TaskDetailAPIView(TaskObjectPermissionMixin, APIView):
    """Асинхронно обрабатывает чтение, обновление и удаление задачи."""

    permission_classes = [TaskAccessPermission]

    @extend_schema(
        tags=['tasks'],
        summary='Получить задачу по идентификатору',
        responses=TASK_DETAIL_RESPONSES,
    )
    async def get(self, request: Request, task_id: int) -> Response:
        """Возвращает детальную информацию по задаче."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        return await self.task_response(request, task)

    @extend_schema(
        tags=['tasks'],
        summary='Частично обновить задачу',
        request=TaskSerializer,
        responses=TASK_DETAIL_RESPONSES,
    )
    async def patch(self, request: Request, task_id: int) -> Response:
        """Обновляет задачу через сериализатор и сервисный слой."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        serializer = await run_sync(build_task_serializer, request=request, instance=task, data=request.data)
        await run_sync(serializer.is_valid, raise_exception=True)
        updated_task = await run_sync(serializer.save)
        return await self.task_response(request, updated_task)

    @extend_schema(
        tags=['tasks'],
        summary='Удалить задачу',
        responses=TASK_DELETE_RESPONSES,
    )
    async def delete(self, request: Request, task_id: int) -> Response:
        """Удаляет задачу, если это делает её автор."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        await run_sync(task.delete)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskCompleteAPIView(TaskObjectPermissionMixin, APIView):
    """Асинхронно переводит задачу в завершённое состояние."""

    permission_classes = [TaskAccessPermission]
    serializer_class = TaskSerializer

    @extend_schema(
        tags=['tasks'],
        summary='Завершить задачу',
        request=None,
        responses=TASK_DETAIL_RESPONSES,
    )
    async def post(self, request: Request, task_id: int) -> Response:
        """Переводит задачу в статус done."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        updated_task = await run_sync(complete_task, actor=get_request_user(request), task=task)
        return await self.task_response(request, updated_task)


class TaskReopenAPIView(TaskObjectPermissionMixin, APIView):
    """Асинхронно возвращает завершённую задачу в активное состояние."""

    permission_classes = [TaskAccessPermission]
    serializer_class = TaskSerializer

    @extend_schema(
        tags=['tasks'],
        summary='Повторно открыть задачу',
        request=None,
        responses=TASK_DETAIL_RESPONSES,
    )
    async def post(self, request: Request, task_id: int) -> Response:
        """Снимает признак завершённости с задачи."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        updated_task = await run_sync(reopen_task, actor=get_request_user(request), task=task)
        return await self.task_response(request, updated_task)


class TaskCommentListCreateAPIView(TaskObjectPermissionMixin, APIView):
    """Асинхронно читает и создаёт комментарии для задачи."""

    permission_classes = [TaskAccessPermission]

    @extend_schema(
        tags=['comments'],
        summary='Получить комментарии задачи',
        responses=COMMENT_LIST_RESPONSES,
    )
    async def get(self, request: Request, task_id: int) -> Response:
        """Возвращает список комментариев для доступной задачи."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        return Response(await run_sync(serialize_comments, task))

    @extend_schema(
        tags=['comments'],
        summary='Добавить комментарий к задаче',
        request=CommentSerializer,
        responses=COMMENT_CREATE_RESPONSES,
    )
    async def post(self, request: Request, task_id: int) -> Response:
        """Создаёт комментарий через сервисный слой."""
        task = await self.get_task_with_permissions(request=request, task_id=task_id)
        serializer = await run_sync(build_comment_serializer, data=request.data)
        await run_sync(serializer.is_valid, raise_exception=True)
        comment = await run_sync(
            create_comment,
            actor=get_request_user(request),
            task=task,
            text=str(serializer.validated_data['text']),
        )
        return Response(await run_sync(serialize_comment, comment), status=status.HTTP_201_CREATED)
