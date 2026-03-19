"""Маршруты асинхронного REST API приложения задач."""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from .views import (
    TaskCommentListCreateAPIView,
    TaskCompleteAPIView,
    TaskDetailAPIView,
    TaskListCreateAPIView,
    TaskReopenAPIView,
    UserMeAPIView,
)

urlpatterns = [
    path('auth/jwt/create/', TokenObtainPairView.as_view(), name='jwt-create'),
    path('auth/jwt/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('auth/jwt/verify/', TokenVerifyView.as_view(), name='jwt-verify'),
    path('users/me/', UserMeAPIView.as_view(), name='user-me'),
    path('tasks/', TaskListCreateAPIView.as_view(), name='task-list-api'),
    path('tasks/<int:task_id>/', TaskDetailAPIView.as_view(), name='task-detail-api'),
    path('tasks/<int:task_id>/complete/', TaskCompleteAPIView.as_view(), name='task-complete-api'),
    path('tasks/<int:task_id>/reopen/', TaskReopenAPIView.as_view(), name='task-reopen-api'),
    path('tasks/<int:task_id>/comments/', TaskCommentListCreateAPIView.as_view(), name='task-comments-api'),
]
