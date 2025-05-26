from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProjectViewSet,
    TaskViewSet,
    BusinessStatisticsViews,
    UserPersonalStatsView,
    WorkLogViewSet,
    OwnerDashboardView,
    EmployeeDashboardView,
    UserProfileView
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'worklogs', WorkLogViewSet, basename='worklog')

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/business/story-points-monthly/', BusinessStatisticsViews.as_view(),
         name='business-stats-story-points'),
    path('me/statistics/task-completion-chart/', UserPersonalStatsView.as_view(), name='user-personal-task-stats'),
    path('dashboards/owner/', OwnerDashboardView.as_view(), name='owner-dashboard'),
    path('dashboards/employee/', EmployeeDashboardView.as_view(), name='employee-dashboard'),

    path('profile/', UserProfileView.as_view(), name='user_profile'),
]
