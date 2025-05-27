from django.db.models import Count, Sum
from django.utils import timezone
from django.db.models.functions import TruncMonth, TruncWeek
from rest_framework import viewsets, permissions, status  # permissions is used multiple times
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import viewsets, permissions
from rest_framework.filters import SearchFilter  # Import SearchFilter
from .models import User
from .serializers import AssigneeUserSerializer, TeamDetailSerializer  # Import your new serializer
# Remove: from django.contrib.auth.decorators import login_required
# Remove: from django.utils.decorators import method_decorator
from rest_framework.authtoken.models import Token  # Keep for LogoutAPIView if needed
from rest_framework import generics  # Keep for UserRegistrationAPIView

from .models import Project, Task, WorkLog, User
from .permissions import IsProjectOwner, IsAssigneeOrProjectOwner, IsWorkLogOwner
from .serializers import (
    ProjectSerializer, TaskSerializer, WorkLogSerializer, UserSimpleSerializer,  # UserSimpleSerializer is used
    UserRegistrationSerializer  # Keep for UserRegistrationAPIView
)
from .filters import TaskFilter
from .quickchart_helper import get_chart_url
from .chart_templates import (
    get_base_pie_chart_config,
    get_base_bar_chart_config,
    get_base_line_chart_config
)


# Note: some imports like 'permissions', 'APIView', 'Response', 'status'
# were duplicated from the original file. I've kept them where first relevant or used.

class UserRegistrationAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            request.user.auth_token.delete()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except (AttributeError, Token.DoesNotExist):
            return Response({"detail": "Invalid token or user not logged in."}, status=status.HTTP_400_BAD_REQUEST)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().prefetch_related('tasks')
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]  # Default, overridden in get_permissions

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated, IsProjectOwner]
        elif self.action == 'task_status_chart':
            self.permission_classes = [permissions.IsAuthenticated, IsProjectOwner]
        elif self.action == 'project_velocity_chart':
            self.permission_classes = [permissions.IsAuthenticated, IsProjectOwner]
        # else: # For other actions like list, retrieve, create, it will use the class-level default
        # self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()  # Ensure default permissions are applied if not matched

    @action(detail=True, methods=['get'], url_path='velocity-chart', url_name='velocity-chart')
    def project_velocity_chart(self, request, pk=None):
        project = self.get_object()
        three_months_ago = timezone.now() - timezone.timedelta(days=90)

        velocity_data = Task.objects.filter(
            project=project,
            status='DONE',
            story_points__isnull=False,
            updated_at__gte=three_months_ago
        ).annotate(
            period_start=TruncWeek('updated_at')
        ).values('period_start').annotate(
            total_story_points=Sum('story_points')
        ).order_by('period_start')

        if not velocity_data:
            return Response({"message": "Not enough data to calculate project velocity."},
                            status=status.HTTP_404_NOT_FOUND)

        labels = [item['period_start'].strftime('%Y-W%W') for item in velocity_data]
        data = [item['total_story_points'] for item in velocity_data]

        chart_config = get_base_line_chart_config()
        chart_config['data']['labels'] = labels
        chart_config['data']['datasets'][0]['label'] = f'Project Velocity (Story Points per Week)'
        chart_config['data']['datasets'][0]['data'] = data
        chart_config['options']['plugins']['title']['text'] = f'Velocity for Project: {project.name}'

        chart_url = get_chart_url(chart_config)
        if chart_url:
            return Response({'chart_url': chart_url})
        else:
            return Response({'error': 'Could not generate chart URL.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='task-status-chart', url_name='task-status-chart')
    def task_status_chart(self, request, pk=None):
        project = self.get_object()
        task_statuses = project.tasks.values('status').annotate(count=Count('status')).order_by('status')

        if not task_statuses:
            return Response({"message": "No tasks found for this project to generate a chart."},
                            status=status.HTTP_404_NOT_FOUND)

        labels = [item['status'] for item in task_statuses]
        data = [item['count'] for item in task_statuses]

        chart_config = get_base_pie_chart_config()
        chart_config['data']['labels'] = labels
        chart_config['data']['datasets'][0]['data'] = data
        chart_config['options']['plugins']['title']['text'] = f'Task Status Distribution for {project.name}'

        chart_url = get_chart_url(chart_config)
        if chart_url:
            return Response({'chart_url': chart_url})
        else:
            return Response({'error': 'Could not generate chart URL.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BusinessStatisticsViews(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        # Add print statements here if you need to debug this specific view's request
        # print("BusinessStatisticsViews HEADERS:", request.headers)
        # print("BusinessStatisticsViews USER:", request.user)
        one_year_ago = timezone.now() - timezone.timedelta(days=365)

        completed_tasks_monthly = Task.objects.filter(
            status='DONE',
            updated_at__gte=one_year_ago,
            story_points__isnull=False
        ).annotate(
            month=TruncMonth('updated_at')
        ).values('month').annotate(
            total_story_points=Sum('story_points')
        ).order_by('month')

        if not completed_tasks_monthly:
            return Response({"message": "No completed tasks with story points found for the last year."},
                            status=status.HTTP_404_NOT_FOUND)

        labels = [item['month'].strftime('%Y-%m') for item in completed_tasks_monthly]
        data = [item['total_story_points'] for item in completed_tasks_monthly]

        chart_config = get_base_bar_chart_config()
        chart_config['data']['labels'] = labels
        chart_config['data']['datasets'][0]['label'] = 'Completed Story Points'
        chart_config['data']['datasets'][0]['data'] = data
        chart_config['options']['plugins']['title']['text'] = 'Monthly Completed Story Points (Last Year)'

        chart_url = get_chart_url(chart_config)
        if chart_url:
            return Response({'chart_url': chart_url})
        else:
            return Response({'error': 'Could not generate chart URL.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserPersonalStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        one_year_ago = timezone.now() - timezone.timedelta(days=365)

        completed_tasks_monthly = Task.objects.filter(
            assignee=user,
            status='DONE',
            updated_at__gte=one_year_ago
        ).annotate(
            month=TruncMonth('updated_at')
        ).values('month').annotate(
            tasks_count=Count('id')
        ).order_by('month')

        if not completed_tasks_monthly:
            return Response({"message": "You have no completed tasks in the last year."},
                            status=status.HTTP_404_NOT_FOUND)

        labels = [item['month'].strftime('%Y-%m') for item in completed_tasks_monthly]
        data = [item['tasks_count'] for item in completed_tasks_monthly]

        chart_config = get_base_line_chart_config()
        chart_config['data']['labels'] = labels
        chart_config['data']['datasets'][0]['label'] = 'My Completed Tasks'
        chart_config['data']['datasets'][0]['data'] = data
        chart_config['options']['plugins']['title']['text'] = 'My Monthly Task Completions (Last Year)'

        chart_url = get_chart_url(chart_config)
        if chart_url:
            return Response({'chart_url': chart_url})
        else:
            return Response({'error': 'Could not generate chart URL.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().select_related('project', 'assignee')
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]  # Default, overridden in get_permissions
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TaskFilter
    search_fields = ['name', 'description', 'project__name']
    ordering_fields = ['created_at', 'deadline', 'status', 'name']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated, IsAssigneeOrProjectOwner]
        elif self.action in ['start_progress', 'mark_as_done']:
            self.permission_classes = [permissions.IsAuthenticated, IsAssigneeOrProjectOwner]
        # else: # For other actions like list, retrieve, create
        # self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    @action(detail=True, methods=['post'], url_path='start-progress')
    def start_progress(self, request, pk=None):
        task = self.get_object()
        if task.status == 'TODO':
            task.status = 'IN_PROGRESS'
            task.save()
            return Response({'status': 'Task moved to In Progress', 'task_status': task.status})
        return Response({'status': 'Task cannot be moved to In Progress from current state'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='mark-as-done')
    def mark_as_done(self, request, pk=None):
        task = self.get_object()
        if task.status == 'IN_PROGRESS':
            task.status = 'DONE'
            task.updated_at = timezone.now()
            task.save()
            return Response({'status': 'Task marked as Done', 'task_status': task.status})
        return Response({'status': 'Task cannot be marked as Done from current state'},
                        status=status.HTTP_400_BAD_REQUEST)


class WorkLogViewSet(viewsets.ModelViewSet):
    queryset = WorkLog.objects.all()
    serializer_class = WorkLogSerializer
    permission_classes = [permissions.IsAuthenticated]  # Default, can be overridden

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or (hasattr(user, 'role') and user.role == 'admin'):
            return WorkLog.objects.all()
        # Ensure user is authenticated before trying to filter by it
        if user.is_authenticated:
            return WorkLog.objects.filter(user=user)
        return WorkLog.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            # Ensure IsWorkLogOwner implies IsAuthenticated or add IsAuthenticated explicitly
            self.permission_classes = [permissions.IsAuthenticated, IsWorkLogOwner]
        return super().get_permissions()


class OwnerDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        if not (user.is_staff or (hasattr(user, 'role') and user.role == 'owner')):
            return Response({"detail": "Not authorized. Owner access required."}, status=status.HTTP_403_FORBIDDEN)

        owned_projects = Project.objects.filter(owner=user)
        active_projects_count = owned_projects.filter(tasks__status__in=['TODO', 'IN_PROGRESS']).distinct().count()
        total_projects_count = owned_projects.count()

        tasks_in_owned_projects = Task.objects.filter(project__owner=user)
        total_tasks = tasks_in_owned_projects.count()
        todo_tasks = tasks_in_owned_projects.filter(status='TODO').count()
        inprogress_tasks = tasks_in_owned_projects.filter(status='IN_PROGRESS').count()
        done_tasks = tasks_in_owned_projects.filter(status='DONE').count()

        projects_data = ProjectSerializer(owned_projects, many=True, context={'request': request}).data

        dashboard_data = {
            'summary_stats': {
                'total_projects': total_projects_count,
                'active_projects': active_projects_count,
                'total_tasks': total_tasks,
                'tasks_todo': todo_tasks,
                'tasks_inprogress': inprogress_tasks,
                'tasks_done': done_tasks,
            },
            'projects_list': projects_data,
        }
        return Response(dashboard_data)


class EmployeeDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user

        assigned_task_projects_ids = Task.objects.filter(assignee=user).values_list('project_id', flat=True).distinct()

        # Ensure user.team exists and is a manager before calling .all()
        user_teams_ids = []
        if hasattr(user, 'team') and hasattr(user.team, 'all'):
            user_teams_ids = user.team.all().values_list('id', flat=True)

        team_projects_ids = Project.objects.filter(team__id__in=user_teams_ids).values_list('id', flat=True).distinct()

        all_involved_project_ids = set(list(assigned_task_projects_ids) + list(team_projects_ids))

        involved_projects = Project.objects.filter(id__in=all_involved_project_ids)
        projects_data = ProjectSerializer(involved_projects, many=True, context={'request': request}).data

        current_tasks = Task.objects.filter(assignee=user, status__in=['TODO', 'IN_PROGRESS'])
        current_tasks_data = TaskSerializer(current_tasks, many=True, context={'request': request}).data

        dashboard_data = {
            'my_projects': projects_data,
            'my_teams': [],  # Placeholder, as team data structure for serializer might be needed
            'my_current_tasks': current_tasks_data,
        }
        return Response(dashboard_data)




class UserListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
    serializer_class = AssigneeUserSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only logged-in users can see other users
    filter_backends = [SearchFilter]
    search_fields = ['username', 'first_name', 'last_name', 'email']  # Fields for ?search= query


# REMOVE @method_decorator(login_required, name='dispatch')
class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # This is correct and uses DRF auth

    def get(self, request, *args, **kwargs):
        # For debugging, you can add these print statements:
        # print("UserProfileView HEADERS:", request.headers)
        # print("UserProfileView META HTTP_AUTHORIZATION:", request.META.get('HTTP_AUTHORIZATION'))
        # print("UserProfileView USER:", request.user, "Authenticated:", request.user.is_authenticated)

        user = request.user
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': getattr(user, 'phone_number', None),
            'role': getattr(user, 'role', None),
        }
        return Response(user_data)

class EmployeeDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user

        assigned_task_projects_ids = Task.objects.filter(assignee=user).values_list('project_id', flat=True).distinct()

        # Get Team objects the user is a member of
        user_teams = user.team.all().prefetch_related('members', 'owner') # Use the reverse accessor 'team' from User model
        teams_data = TeamDetailSerializer(user_teams, many=True, context={'request': request}).data

        team_projects_ids = Project.objects.filter(team__in=user_teams).values_list('id', flat=True).distinct()

        all_involved_project_ids = set(list(assigned_task_projects_ids) + list(team_projects_ids))
        involved_projects = Project.objects.filter(id__in=all_involved_project_ids)
        projects_data = ProjectSerializer(involved_projects, many=True, context={'request': request}).data

        current_tasks = Task.objects.filter(assignee=user, status__in=['TODO', 'IN_PROGRESS'])
        current_tasks_data = TaskSerializer(current_tasks, many=True, context={'request': request}).data

        dashboard_data = {
            'my_projects': projects_data,
            'my_teams': teams_data, # This will now contain the serialized team data
            'my_current_tasks': current_tasks_data,
        }
        return Response(dashboard_data)
