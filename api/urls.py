from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_nested import routers


from .views import (
    ProjectViewSet,
    TaskViewSet,
    BusinessStatisticsViews,
    UserPersonalStatsView,
    WorkLogViewSet,
    OwnerDashboardView,
    EmployeeDashboardView,
    UserProfileView,
    UserRegistrationAPIView,
    LogoutAPIView,
    UserListViewSet,
    TeamViewSet,
    TeamMemberViewSet,
    TaskCommentViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'worklogs', WorkLogViewSet, basename='worklog')
router.register(r'users', UserListViewSet, basename='userlist')
router.register(r'teams', TeamViewSet, basename='team')


tasks_router = routers.NestedSimpleRouter(router, r'tasks', lookup='task')
tasks_router.register(r'comments', TaskCommentViewSet, basename='task-comments')

teams_router = routers.NestedSimpleRouter(router, r'teams', lookup='team')
teams_router.register(r'members', TeamMemberViewSet, basename='team-members')


urlpatterns = [
    path('', include(router.urls)),
    path('', include(tasks_router.urls)),
    path('', include(teams_router.urls)),

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
