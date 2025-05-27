from django.urls import path, include
from rest_framework.routers import DefaultRouter

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token  # For login
from .views import (
    ProjectViewSet,
    TaskViewSet,
    BusinessStatisticsViews,
    UserPersonalStatsView,
    WorkLogViewSet,
    OwnerDashboardView,
    EmployeeDashboardView,
    UserProfileView,
    UserRegistrationAPIView,  # <-- Import new registration view
    LogoutAPIView,
    UserListViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'worklogs', WorkLogViewSet, basename='worklog')
router.register(r'users', UserListViewSet, basename='userlist')
# If you want a /users endpoint for listing (admin) or retrieving users:
# from .views import UserViewSet # You would need to create this
# router.register(r'users', UserViewSet, basename='user')


urlpatterns = [
    path('', include(router.urls)),

    # Auth
    path('auth/register/', UserRegistrationAPIView.as_view(), name='auth-register'),
    path('auth/login/', obtain_auth_token, name='auth-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='auth-logout'),

    path('statistics/business/story-points-monthly/', BusinessStatisticsViews.as_view(),
         name='business-stats-story-points'),
    path('me/statistics/task-completion-chart/', UserPersonalStatsView.as_view(), name='user-personal-task-stats'),
    path('dashboards/owner/', OwnerDashboardView.as_view(), name='owner-dashboard'),
    path('dashboards/employee/', EmployeeDashboardView.as_view(), name='employee-dashboard'),

    path('profile/', UserProfileView.as_view(), name='user_profile'),

]
