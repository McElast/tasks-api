"""Маршруты HTML-интерфейса приложения задач."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.task_list_view, name='task-list'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task-create'),
    path('tasks/<int:task_id>/', views.task_detail_view, name='task-detail'),
    path('tasks/<int:task_id>/edit/', views.TaskUpdateView.as_view(), name='task-update'),
    path('tasks/<int:task_id>/delete/', views.TaskDeleteView.as_view(), name='task-delete'),
    path('tasks/<int:task_id>/complete/', views.complete_task_view, name='task-complete'),
    path('tasks/<int:task_id>/reopen/', views.reopen_task_view, name='task-reopen'),
    path('tasks/<int:task_id>/comments/create/', views.TaskCommentCreateView.as_view(), name='task-comment-create'),
]
