import json

import requests
from django.test import TestCase
from django.urls import reverse
from .models import User, Team, Project, Task, WorkLog
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from django.utils import timezone
from datetime import timedelta, date as datetime_date
from decimal import Decimal
from unittest.mock import patch

from .quickchart_helper import get_chart_url
from .serializers import UserRegistrationSerializer, AssigneeUserSerializer, TaskSerializer, WorkLogSerializer


class UserModelTest(TestCase):
    def setUp(self):
        self.team_main_owner = User.objects.create_user(username='teamowner_model', password='password')
        self.team = Team.objects.create(name='Test Team Model', owner=self.team_main_owner)

        self.user_admin = User.objects.create_user(
            username='admin_user_model',
            email='admin_model@example.com',
            password='password123',
            role='admin',
            first_name='Admin',
            last_name='User',
            phone_number='1112223344'
        )
        self.user_employee = User.objects.create_user(
            username='employee_user_model',
            email='employee_model@example.com',
            password='password123',
            role='employee',
            first_name='Employee',
            last_name='User'
        )
        self.user_admin.team.add(self.team)

    def test_user_creation(self):
        self.assertEqual(self.user_admin.username, 'admin_user_model')
        self.assertEqual(self.user_admin.email, 'admin_model@example.com')
        self.assertTrue(self.user_admin.check_password('password123'))
        self.assertEqual(self.user_admin.role, 'admin')
        self.assertEqual(self.user_admin.first_name, 'Admin')
        self.assertEqual(self.user_admin.last_name, 'User')
        self.assertEqual(self.user_admin.phone_number, '1112223344')
        self.assertTrue(self.user_admin.is_active)
        self.assertFalse(self.user_admin.is_staff)
        self.assertFalse(self.user_admin.is_superuser)

    def test_user_str_representation(self):
        expected_str = f"{self.user_admin.username} ({self.user_admin.email})"
        self.assertEqual(str(self.user_admin), expected_str)

    def test_user_default_role(self):
        self.assertEqual(self.user_employee.role, 'employee')

    def test_user_team_membership(self):
        self.assertIn(self.team, self.user_admin.team.all())
        self.assertEqual(self.team.members.count(), 1)
        self.assertEqual(self.team.members.first(), self.user_admin)
        self.assertEqual(self.user_employee.team.count(), 0)


class UserRegistrationSerializerTest(APITestCase):
    def test_registration_password_mismatch(self):
        data = {
            "username": "testuser_pwmiss", "email": "pwmiss@example.com",
            "password": "password123", "password2": "password456"
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_registration_existing_username(self):
        User.objects.create_user(username='existinguser', email='unique@example.com', password='password123')
        data = {
            "username": "ExistingUser", "email": "newemail@example.com",
            "password": "password123", "password2": "password123"
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_registration_existing_email(self):
        User.objects.create_user(username='anotheruser', email='existing@example.com', password='password123')
        data = {
            "username": "newuser_email", "email": "EXISTING@example.com",
            "password": "password123", "password2": "password123"
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_registration_optional_fields_not_provided(self):
        data = {
            "username": "minimaluser", "email": "minimal@example.com",
            "password": "aVeryComplexPassword!123",
            "password2": "aVeryComplexPassword!123"
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.phone_number, '')


class AssigneeUserSerializerTest(TestCase):
    def test_assignee_display_name_username_only(self):
        user = User.objects.create_user(username='only_username')
        serializer = AssigneeUserSerializer(instance=user)
        self.assertEqual(serializer.data['display_name'], 'only_username')


class TeamModelTest(TestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(username='team_owner_model', password='password')

    def test_team_creation(self):
        team = Team.objects.create(name='Another Team Model', owner=self.owner_user)
        self.assertEqual(team.name, 'Another Team Model')
        self.assertEqual(team.owner, self.owner_user)

    def test_team_str_representation(self):
        team = Team.objects.create(name='Marketing Model', owner=self.owner_user)
        expected_str = f"{team.name} (Owner: {self.owner_user})"
        self.assertEqual(str(team), expected_str)


class TaskSerializerValidationTest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='task_ser_owner', password='password')
        self.project = Project.objects.create(name='Task Serializer Project', owner=self.owner)
        self.user_for_assignee = User.objects.create_user(username='task_ser_assignee', password='password')

    def test_task_serializer_invalid_project_id(self):
        data = {
            "name": "Task with bad project", "project_id": 99999,
            "status": "TODO", "assignee_id": self.user_for_assignee.id
        }
        serializer = TaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('project_id', serializer.errors)

    def test_task_serializer_invalid_assignee_id(self):
        data = {
            "name": "Task with bad assignee", "project_id": self.project.id,
            "status": "TODO", "assignee_id": 999995
        }
        serializer = TaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('assignee_id', serializer.errors)

    def test_task_serializer_assignee_id_null(self):
        data = {
            "name": "Task no assignee", "project_id": self.project.id,
            "status": "TODO", "assignee_id": None
        }
        serializer = TaskSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        task = serializer.save()
        self.assertIsNone(task.assignee)


class UserProfileViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='profileuser', email='profile@example.com', password='testpassword',
            first_name='Profile', last_name='User', phone_number='1234567890', role='employee'
        )
        self.token = Token.objects.create(user=self.user)
        self.profile_url = reverse('user_profile')

    def test_user_profile_view_authenticated(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {
            'id': self.user.id, 'username': self.user.username, 'email': self.user.email,
            'first_name': self.user.first_name, 'last_name': self.user.last_name,
            'phone_number': self.user.phone_number, 'role': self.user.role,
        }
        self.assertEqual(response.json(), expected_data)

    def test_user_profile_view_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProjectAPITests(APITestCase):
    def setUp(self):
        self.user_owner = User.objects.create_user(username='api_owner', password='password123', role='owner')
        self.owner_token = Token.objects.create(user=self.user_owner)
        self.user_employee = User.objects.create_user(username='api_employee', password='password123', role='employee')
        self.employee_token = Token.objects.create(user=self.user_employee)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.owner_token.key)

        self.project1 = Project.objects.create(name='Project Alpha API', description='Description Alpha API',
                                               owner=self.user_owner)
        self.project2 = Project.objects.create(name='Project Beta API', description='Description Beta API',
                                               owner=self.user_owner)

        self.project_list_url = reverse('project-list')

    def _get_project_detail_url(self, pk):
        return reverse('project-detail', kwargs={'pk': pk})

    def test_create_project_as_owner(self):
        data = {'name': 'Project Gamma API', 'description': 'New project API'}
        response = self.client.post(self.project_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 3)
        created_project = Project.objects.get(name='Project Gamma API')
        self.assertEqual(created_project.owner, "broken something")

    def test_list_projects_as_owner(self):
        response = self.client.get(self.project_list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data.get('count'), 2)
        self.assertEqual(len(response_data.get('results', [])), 2)

    def test_retrieve_project_as_owner(self):
        response = self.client.get(self._get_project_detail_url(self.project1.pk), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('name'), self.project1.name)

    def test_update_project_by_owner(self):
        data = {'name': 'Project Alpha Updated API', 'description': 'Updated Description API'}
        response = self.client.put(self._get_project_detail_url(self.project1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.name, 'Project Alpha Updated API')

    def test_partial_update_project_by_owner(self):
        data = {'description': 'Partially Updated Description API'}
        response = self.client.patch(self._get_project_detail_url(self.project1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.description, 'Partially Updated Description API')

    def test_update_project_by_non_owner_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employee_token.key)
        data = {'name': 'Attempt Update Fail API', 'description': 'Updated Description'}
        response = self.client.put(self._get_project_detail_url(self.project1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_project_by_owner(self):
        response = self.client.delete(self._get_project_detail_url(self.project1.pk), format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Project.objects.count(), 1)

    def test_delete_project_by_non_owner_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employee_token.key)
        response = self.client.delete(self._get_project_detail_url(self.project1.pk), format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_endpoints_unauthenticated(self):
        self.client.credentials()
        self.assertEqual(self.client.post(self.project_list_url, {'name': 'Unauth Test'}, format='json').status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.project_list_url, format='json').status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self._get_project_detail_url(self.project1.pk), format='json').status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.put(self._get_project_detail_url(self.project1.pk), {}, format='json').status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(self._get_project_detail_url(self.project1.pk), format='json').status_code,
                         status.HTTP_401_UNAUTHORIZED)

    @patch('api.views.get_chart_url')
    def test_project_task_status_chart_by_owner(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/pie_owner'
        Task.objects.create(project=self.project1, name="Chart Task Owner", status="TODO", assignee=self.user_owner)
        url = reverse('project-task-status-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('chart_url'), 'http://fakechart.url/pie_owner')
        mock_get_chart_url.assert_called_once()

    @patch('api.views.get_chart_url')
    def test_project_task_status_chart_by_employee_forbidden(self, mock_get_chart_url):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employee_token.key)
        url = reverse('project-task-status-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_project_task_status_chart_unauthenticated(self, mock_get_chart_url):
        self.client.credentials()
        url = reverse('project-task-status-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart_by_owner(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/velocity_owner'
        Task.objects.create(project=self.project1, name="Vel Task Owner", status="DONE", assignee=self.user_owner,
                            story_points=5, updated_at=timezone.now())
        url = reverse('project-velocity-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('chart_url'), 'http://fakechart.url/velocity_owner')
        mock_get_chart_url.assert_called_once()

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart_by_employee_forbidden(self, mock_get_chart_url):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employee_token.key)
        url = reverse('project-velocity-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart_unauthenticated(self, mock_get_chart_url):
        self.client.credentials()
        url = reverse('project-velocity-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart_no_data(self, mock_get_chart_url):
        Task.objects.filter(project=self.project1, status='DONE').delete()
        url = reverse('project-velocity-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Not enough data", response.json().get("message"))
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart_api_failure(self, mock_get_chart_url):
        mock_get_chart_url.return_value = None
        Task.objects.create(project=self.project1, name="Vel Task For Fail", status="DONE", assignee=self.user_owner,
                            story_points=5, updated_at=timezone.now())
        url = reverse('project-velocity-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Could not generate chart URL", response.json().get("error"))
        mock_get_chart_url.assert_called_once()

    @patch('api.views.get_chart_url')
    def test_project_task_status_chart_api_failure(self, mock_get_chart_url):
        mock_get_chart_url.return_value = None
        Task.objects.create(project=self.project1, name="Status Task For Fail", status="TODO", assignee=self.user_owner)
        url = reverse('project-task-status-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Could not generate chart URL", response.json().get("error"))
        mock_get_chart_url.assert_called_once()


class TaskAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='task_owner_perms', password='password123', role='owner')
        self.owner_token = Token.objects.create(user=self.owner)
        self.assignee = User.objects.create_user(username='task_assignee_perms', password='password123',
                                                 role='employee')
        self.assignee_token = Token.objects.create(user=self.assignee)
        self.other_user = User.objects.create_user(username='task_other_perms', password='password123', role='employee')
        self.other_user_token = Token.objects.create(user=self.other_user)

        self.project = Project.objects.create(name='Task Project Perms', owner=self.owner)
        self.task1 = Task.objects.create(project=self.project, name='Task One Perms', status='TODO',
                                         assignee=self.assignee, story_points=5, deadline=datetime_date(2025, 12, 1))
        self.task2 = Task.objects.create(project=self.project, name='Task Two Perms', status='IN_PROGRESS',
                                         assignee=self.owner, deadline=datetime_date(2025, 11, 1))

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.owner_token.key)
        self.task_list_url = reverse('task-list')

    def _get_task_detail_url(self, pk):
        return reverse('task-detail', kwargs={'pk': pk})

    def test_create_task_as_authenticated_user(self):  # e.g., owner
        data = {'name': 'Task Three Perms', 'project_id': self.project.id, 'status': 'TODO',
                'assignee_id': self.assignee.id, 'story_points': 3}
        response = self.client.post(self.task_list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 3)

    def test_list_tasks_as_authenticated_user(self):
        response = self.client.get(self.task_list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('count'), 2)

    def test_retrieve_task_as_owner(self):
        response = self.client.get(self._get_task_detail_url(self.task1.pk), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('name'), self.task1.name)

    def test_retrieve_task_as_assignee(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.assignee_token.key)
        response = self.client.get(self._get_task_detail_url(self.task1.pk), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('name'), self.task1.name)

    def test_update_task_by_owner(self):
        data = {'name': 'Task Updated by Owner Perms', 'status': 'DONE', 'project_id': self.project.id,
                'assignee_id': self.assignee.id}
        response = self.client.put(self._get_task_detail_url(self.task1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_task_by_assignee(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.assignee_token.key)
        data = {'name': 'Task Updated by Assignee Perms', 'status': 'IN_PROGRESS', 'project_id': self.project.id,
                'assignee_id': self.assignee.id}
        response = self.client.put(self._get_task_detail_url(self.task1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_task_by_other_user_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.other_user_token.key)
        data = {'name': 'Attempt Update Fail Perms'}
        response = self.client.put(self._get_task_detail_url(self.task1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_task_by_owner(self):
        response = self.client.delete(self._get_task_detail_url(self.task1.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_task_by_assignee(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.assignee_token.key)
        response = self.client.delete(self._get_task_detail_url(self.task1.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_task_by_other_user_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.other_user_token.key)
        response = self.client.delete(self._get_task_detail_url(self.task2.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_endpoints_unauthenticated(self):
        self.client.credentials()
        self.assertEqual(self.client.post(self.task_list_url, {}, format='json').status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.task_list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self._get_task_detail_url(self.task1.pk)).status_code,
                         status.HTTP_401_UNAUTHORIZED)

    def test_task_action_start_progress_by_assignee(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.assignee_token.key)
        url = reverse('task-start-progress', kwargs={'pk': self.task1.pk})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.status, 'IN_PROGRESS')

    def test_task_action_mark_as_done_by_owner_of_task_assigned_to_owner(self):
        # task2 is assigned to owner, status is IN_PROGRESS
        url = reverse('task-mark-as-done', kwargs={'pk': self.task2.pk})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task2.refresh_from_db()
        self.assertEqual(self.task2.status, 'DONE')

    def test_task_filter_by_status_as_owner(self):
        response = self.client.get(self.task_list_url + '?status=TODO', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get('count'), 1)  # task1 is TODO
        if data.get('results'):
            self.assertEqual(data['results'][0].get('name'), self.task1.name)

    def test_retrieve_task_as_staff_member(self):
        # staff_user is not owner of project, not assignee of task1
        staff_user = User.objects.create_user(username='staff_task_user', password='password123', is_staff=True)
        staff_token = Token.objects.create(user=staff_user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + staff_token.key)

        # task1 is owned by self.owner, assigned to self.assignee
        response = self.client.get(self._get_task_detail_url(self.task1.pk), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('name'), self.task1.name)

    def test_update_task_by_staff_member_forbidden(self):
        # staff_user is not owner of project, not assignee of task1
        staff_user = User.objects.create_user(username='staff_task_user_perm', password='password123', is_staff=True)
        staff_token = Token.objects.create(user=staff_user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + staff_token.key)

        data = {'name': 'Attempt Update by Staff'}
        response = self.client.put(self._get_task_detail_url(self.task1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_action_start_progress_invalid_state(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.assignee_token.key)
        self.task1.status = 'IN_PROGRESS'  # Change state from TODO
        self.task1.save()
        url = reverse('task-start-progress', kwargs={'pk': self.task1.pk})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be moved to In Progress", response.json().get('status'))

    def test_task_action_mark_as_done_invalid_state(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.assignee_token.key)
        # self.task1 is initially TODO. For this test, it needs to be NOT IN_PROGRESS.
        self.task1.status = 'TODO'
        self.task1.save()
        url = reverse('task-mark-as-done', kwargs={'pk': self.task1.pk})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be marked as Done", response.json().get('status'))


class ChartViewTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='chartview_owner', password='password123', role='owner')
        self.owner_token = Token.objects.create(user=self.owner)
        self.assignee = User.objects.create_user(username='chartview_assignee', password='password123', role='employee')
        self.assignee_token = Token.objects.create(user=self.assignee)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.owner_token.key)

        self.project = Project.objects.create(name='Chart Project Views Test', owner=self.owner)
        Task.objects.create(project=self.project, name='Task A', status='TODO', assignee=self.assignee, story_points=5,
                            updated_at=timezone.now() - timedelta(days=70))
        Task.objects.create(project=self.project, name='Task B', status='IN_PROGRESS', assignee=self.owner,
                            story_points=3, updated_at=timezone.now() - timedelta(days=60))
        Task.objects.create(project=self.project, name='Task C', status='DONE', assignee=self.assignee, story_points=8,
                            updated_at=timezone.now() - timedelta(days=50))
        Task.objects.create(project=self.project, name='Task D', status='DONE', assignee=self.owner, story_points=2,
                            updated_at=timezone.now() - timedelta(days=40))
        Task.objects.create(project=self.project, name='Task E', status='DONE', assignee=self.owner, story_points=1,
                            updated_at=timezone.now() - timedelta(days=10))
        Task.objects.create(project=self.project, name='Assignee Task Done ForChart', status='DONE',
                            assignee=self.assignee, updated_at=timezone.now() - timedelta(days=5))

    @patch('api.views.get_chart_url')
    def test_project_task_status_chart_as_owner(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/piechart_cv'
        url = reverse('project-task-status-chart', kwargs={'pk': self.project.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('chart_url'), 'http://fakechart.url/piechart_cv')
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(chart_config['options']['plugins']['title']['text'],
                         f'Task Status Distribution for {self.project.name}')
        # Counts: TODO:1 (A), IN_PROGRESS:1 (B), DONE:4 (C,D,E, Assignee Task Done ForChart)
        labels = chart_config.get('data', {}).get('labels', [])
        data_values = chart_config.get('data', {}).get('datasets', [{}])[0].get('data', [])
        data_dict = dict(zip(labels, data_values))
        self.assertEqual(data_dict.get('DONE'), 4)
        self.assertEqual(data_dict.get('TODO'), 1)
        self.assertEqual(data_dict.get('IN_PROGRESS'), 1)

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart_as_owner(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/velocitychart_cv'
        Task.objects.filter(project=self.project, name='Task C').update(updated_at=timezone.now() - timedelta(days=80),
                                                                        story_points=8)
        Task.objects.filter(project=self.project, name='Task D').update(updated_at=timezone.now() - timedelta(days=73),
                                                                        story_points=2)
        Task.objects.filter(project=self.project, name='Task E').update(updated_at=timezone.now() - timedelta(days=10),
                                                                        story_points=1)
        # Assignee Task Done ForChart has no story_points, so not included in velocity. Sum = 8+2+1=11
        url = reverse('project-velocity-chart', kwargs={'pk': self.project.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(sum(chart_config.get('data', {}).get('datasets', [{}])[0].get('data', [])), 11)

    @patch('api.views.get_chart_url')
    def test_business_statistics_story_points_monthly(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/business_stats_cv'
        # Tasks C(8), D(2), E(1) = 11 SP.
        Task.objects.create(project=self.project, name='Biz Task Old Month CV', status='DONE', assignee=self.owner,
                            story_points=10, updated_at=timezone.now() - timedelta(days=35))
        # Total = 11 + 10 = 21
        url = reverse('business-stats-story-points')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(sum(chart_config.get('data', {}).get('datasets', [{}])[0].get('data', [])), 21)

    @patch('api.views.get_chart_url')
    def test_user_personal_task_stats_for_owner(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/personal_stats_owner_cv'
        url = reverse('user-personal-task-stats')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Owner: Task B (IN_PROGRESS), Task D (DONE), Task E (DONE). Count = 2
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(sum(chart_config.get('data', {}).get('datasets', [{}])[0].get('data', [])), 2)

    @patch('api.views.get_chart_url')
    def test_user_personal_task_stats_for_assignee(self, mock_get_chart_url):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.assignee_token.key)
        mock_get_chart_url.return_value = 'http://fakechart.url/personal_stats_assignee_cv'
        # Assignee: Task A (TODO), Task C (DONE), Assignee Task Done ForChart (DONE).
        Task.objects.create(project=self.project, name='Assignee Task Done 2 CV', status='DONE', assignee=self.assignee,
                            updated_at=timezone.now() - timedelta(days=3))
        url = reverse('user-personal-task-stats')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(sum(chart_config.get('data', {}).get('datasets', [{}])[0].get('data', [])), 3)

    @patch('api.views.get_chart_url')
    def test_project_task_status_chart_no_tasks(self, mock_get_chart_url):
        no_task_owner = User.objects.create_user(username='notaskowner', password='password123', role='owner')
        no_task_token = Token.objects.create(user=no_task_owner)
        no_task_project = Project.objects.create(name='No Task Project', owner=no_task_owner)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + no_task_token.key)
        url = reverse('project-task-status-chart', kwargs={'pk': no_task_project.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("No tasks found", response.json().get("message", ""))

    @patch('api.views.get_chart_url')
    def test_business_statistics_no_data(self, mock_get_chart_url):
        Task.objects.filter(status='DONE', story_points__isnull=False).delete()
        url = reverse('business-stats-story-points')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("No completed tasks with story points", response.json().get("message"))
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_business_statistics_api_failure(self, mock_get_chart_url):
        mock_get_chart_url.return_value = None
        Task.objects.create(project=self.project, name='Biz Task For Fail Chart', status='DONE', assignee=self.owner,
                            story_points=10, updated_at=timezone.now() - timedelta(days=35))
        url = reverse('business-stats-story-points')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        mock_get_chart_url.assert_called_once()

    @patch('api.views.get_chart_url')
    def test_user_personal_stats_no_data(self, mock_get_chart_url):
        Task.objects.filter(assignee=self.owner, status='DONE').delete()
        url = reverse('user-personal-task-stats')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("You have no completed tasks", response.json().get("message"))
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_user_personal_stats_api_failure(self, mock_get_chart_url):
        mock_get_chart_url.return_value = None
        Task.objects.create(project=self.project, name='My Task For Fail Chart', status='DONE', assignee=self.owner,
                            updated_at=timezone.now() - timedelta(days=10))
        url = reverse('user-personal-task-stats')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        mock_get_chart_url.assert_called_once()


class QuickChartHelperTests(APITestCase):
    @patch('api.quickchart_helper.requests.post')
    def test_get_chart_url_success(self, mock_post):
        mock_response = mock_post.return_value
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'url': 'http://successful.chart.url'}

        chart_config_dict = {'type': 'bar', 'data': {}}
        expected_chart_json_str = json.dumps(chart_config_dict)
        url = get_chart_url(chart_config_dict)
        self.assertEqual(url, 'http://successful.chart.url')
        mock_post.assert_called_once()

        actual_payload_sent_to_post = mock_post.call_args[1]['json']
        self.assertEqual(actual_payload_sent_to_post['chart'], expected_chart_json_str)
        self.assertEqual(actual_payload_sent_to_post['width'], 500)

        @patch('api.quickchart_helper.requests.post')
        def test_get_chart_url_json_decode_error(self, mock_post):
            mock_response = mock_post.return_value
            mock_response.raise_for_status.return_value = None
            mock_response.json.side_effect = json.JSONDecodeError("Test decode error", "doc",
                                                                  0)

            chart_config = {'type': 'bar', 'data': {}}
            url = get_chart_url(chart_config)

            self.assertIsNone(url)

        @patch('api.quickchart_helper.requests.post')
        def test_get_chart_url_chart_config_as_string(self, mock_post):
            mock_response = mock_post.return_value
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'url': 'http://string.config.url'}

            chart_config_str = '{"type": "line", "data": {}}'
            url = get_chart_url(chart_config_str, width=300, height=150, device_pixel_ratio=2.0, format='svg',
                                background_color='#FFFFFF')

            self.assertEqual(url, 'http://string.config.url')
            mock_post.assert_called_once()
            call_args_json = mock_post.call_args[1]['json']
            self.assertEqual(call_args_json['chart'], chart_config_str)
            self.assertEqual(call_args_json['width'], 300)
            self.assertEqual(call_args_json['height'], 150)
            self.assertEqual(call_args_json['devicePixelRatio'], 2.0)
            self.assertEqual(call_args_json['format'], 'svg')
            self.assertEqual(call_args_json['bkg'], '#FFFFFF')


class WorkLogAPITests(APITestCase):
    def setUp(self):
        self.loguser1 = User.objects.create_user(username='workloguser1', password='password123', role='employee')
        self.loguser1_token = Token.objects.create(user=self.loguser1)

        self.admin_user = User.objects.create_user(username='worklogadmin', password='password123', role='admin',
                                                   is_staff=True)
        self.admin_token = Token.objects.create(user=self.admin_user)

        self.project_owner = User.objects.create_user(username='worklogprojowner', password='password123', role='owner')

        self.project = Project.objects.create(name='WorkLog Project', owner=self.project_owner)
        self.task = Task.objects.create(project=self.project, name='WorkLog Task', assignee=self.loguser1)

        self.worklog_of_loguser1 = WorkLog.objects.create(
            user=self.loguser1, task=self.task,
            date=timezone.now().date() - timedelta(days=1),
            hours_spent='3.00', description="Loguser1's old worklog"
        )

        self.list_create_url = reverse('worklog-list')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.loguser1_token.key)

    def _get_detail_url(self, pk):
        return reverse('worklog-detail', kwargs={'pk': pk})

    def test_create_worklog_for_task_as_loguser1(self):
        data = {
            'task_id': self.task.id, 'date': timezone.now().date().isoformat(),
            'hours_spent': '2.50', 'description': 'New worklog'
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WorkLog.objects.count(), 2)
        new_log = WorkLog.objects.get(pk=response.json()['id'])
        self.assertEqual(new_log.user, self.loguser1)
        self.assertEqual(new_log.description, 'New worklog')

    def test_create_worklog_unauthenticated(self):
        self.client.credentials()  # Clear auth
        data = {'task_id': self.task.id, 'hours_spent': '1.00'}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_own_worklogs_as_loguser1(self):
        response = self.client.get(self.list_create_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('count'), 1)
        self.assertEqual(response.json().get('results')[0].get('id'), self.worklog_of_loguser1.id)

    def test_list_all_worklogs_as_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        WorkLog.objects.create(user=self.admin_user, project=self.project, date=timezone.now().date(),
                               hours_spent='1.00')
        response = self.client.get(self.list_create_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('count'), 2)

    def test_retrieve_own_worklog_as_loguser1(self):
        response = self.client.get(self._get_detail_url(self.worklog_of_loguser1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('id'), self.worklog_of_loguser1.id)

    def test_retrieve_others_worklog_as_loguser1_not_found(self):
        other_worklog = WorkLog.objects.create(user=self.admin_user, project=self.project, date=timezone.now().date(),
                                               hours_spent='2.00')
        response = self.client.get(self._get_detail_url(other_worklog.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_own_worklog_as_loguser1(self):
        data = {'description': 'Updated by loguser1', 'hours_spent': '9.99', 'task_id': self.task.id,
                'date': self.worklog_of_loguser1.date.isoformat()}
        response = self.client.put(self._get_detail_url(self.worklog_of_loguser1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.worklog_of_loguser1.refresh_from_db()
        self.assertEqual(self.worklog_of_loguser1.description, 'Updated by loguser1')

    def test_update_others_worklog_as_loguser1_forbidden(self):
        other_worklog = WorkLog.objects.create(user=self.admin_user, project=self.project, date=timezone.now().date(),
                                               hours_spent='2.00')
        data = {'description': 'Attempted update by loguser1'}
        response = self.client.patch(self._get_detail_url(other_worklog.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_worklog_as_loguser1(self):
        response = self.client.delete(self._get_detail_url(self.worklog_of_loguser1.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WorkLog.objects.filter(pk=self.worklog_of_loguser1.pk).exists())


class WorkLogSerializerValidationTest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='wl_ser_owner', password='password')
        self.project = Project.objects.create(name='WL Serializer Project', owner=self.owner)
        self.task = Task.objects.create(project=self.project, name='WL Serializer Task', assignee=self.owner)
        self.user = self.owner

    def test_worklog_serializer_both_task_and_project(self):
        data = {
            "task_id": self.task.id, "project_id": self.project.id,
            "date": timezone.now().date().isoformat(), "hours_spent": "1.00",
            "user_id": self.user.id
        }
        serializer_context = {'request': type('Request', (), {'user': self.user})}
        serializer = WorkLogSerializer(data=data, context=serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_worklog_serializer_neither_task_nor_project(self):
        data = {
            "date": timezone.now().date().isoformat(), "hours_spent": "1.00",
            "user_id": self.user.id
        }
        serializer_context = {'request': type('Request', (), {'user': self.user})}
        serializer = WorkLogSerializer(data=data, context=serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_worklog_serializer_update_task_to_none_no_project(self):
        worklog = WorkLog.objects.create(user=self.user, task=self.task, hours_spent="2.00")
        data = {"task_id": None, "project_id": None, "hours_spent": "2.50"}
        serializer_context = {'request': type('Request', (), {'user': self.user})}
        serializer = WorkLogSerializer(instance=worklog, data=data, partial=True, context=serializer_context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)


    def test_worklog_serializer_create_with_project_only(self):
        data = {
            "project_id": self.project.id,
            "date": timezone.now().date().isoformat(),
            "hours_spent": "3.00",
            "description": "Project-level log"
        }
        serializer_context = {'request': type('Request', (), {'user': self.user})}
        serializer = WorkLogSerializer(data=data, context=serializer_context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        worklog = serializer.save()
        self.assertEqual(worklog.project, self.project)
        self.assertIsNone(worklog.task)


class ModelStrRepresentationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='str_user', password='password')
        self.project = Project.objects.create(name='Test Project Str', owner=self.user)
        self.task = Task.objects.create(project=self.project, name='Test Task Str')
        self.worklog = WorkLog.objects.create(user=self.user, task=self.task, hours_spent=Decimal(1.0), date=timezone.now().date())

    def test_project_str_representation(self):
        self.assertEqual(str(self.project), 'Test Project Str')

    def test_task_str_representation(self):
        expected_str = f"Test Task Str (Project: {self.project.name})"
        self.assertEqual(str(self.task), expected_str)

    def test_worklog_str_representation(self):
        expected_str = f"{self.user.username} - 1.00h on {timezone.now().date()}"
        self.assertTrue(str(self.worklog).startswith(f"{self.user.username} - 1.00h on"))
        self.assertEqual(str(self.worklog), expected_str)


class OwnerDashboardViewTest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='dash_owner', password='password', role='owner')
        self.owner_token = Token.objects.create(user=self.owner)
        self.employee = User.objects.create_user(username='dash_employee', password='password', role='employee')
        self.employee_token = Token.objects.create(user=self.employee)
        self.url = reverse('owner-dashboard')

    def test_owner_dashboard_access_by_owner(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.owner_token.key)
        Project.objects.create(name="Owner's Project", owner=self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary_stats', response.data)

    def test_owner_dashboard_access_by_employee_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employee_token.key)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Not authorized", response.data.get('detail'))

    def test_owner_dashboard_access_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class EmployeeDashboardViewTest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='emp_dash_owner', password='password', role='owner')
        self.employee = User.objects.create_user(username='emp_dash_employee', password='password', role='employee')
        self.employee_token = Token.objects.create(user=self.employee)

        self.team_owner = User.objects.create_user(username='emp_dash_team_owner', password='password', role='owner')
        self.team1 = Team.objects.create(name='Team Alpha', owner=self.team_owner)
        self.employee.team.add(self.team1)

        self.project1 = Project.objects.create(name="Assigned Project", owner=self.owner)
        Task.objects.create(project=self.project1, name="Employee Task", assignee=self.employee, status='TODO')

        self.project2 = Project.objects.create(name="Team Project", owner=self.owner)
        self.project2.team.add(self.team1)

        self.url = reverse('employee-dashboard')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.employee_token.key)

    def test_employee_dashboard_structure(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn('my_projects', data)
        self.assertIn('my_teams', data)
        self.assertIn('my_current_tasks', data)

        self.assertEqual(len(data['my_projects']), 2)
        self.assertEqual(len(data['my_teams']), 1)
        self.assertEqual(data['my_teams'][0]['name'], 'Team Alpha')
        self.assertEqual(len(data['my_current_tasks']), 1)
        self.assertEqual(data['my_current_tasks'][0]['name'], 'Employee Task')

    def test_employee_dashboard_no_teams_no_project_tasks(self):
        no_team_employee = User.objects.create_user(username='no_team_emp', password='password', role='employee')
        no_team_token = Token.objects.create(user=no_team_employee)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + no_team_token.key)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(len(data['my_projects']), 0)
        self.assertEqual(len(data['my_teams']), 0)
        self.assertEqual(len(data['my_current_tasks']), 0)

    def test_employee_dashboard_access_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutAPIViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='logout_user', password='password')
        self.token = Token.objects.create(user=self.user)
        self.url = reverse('auth-logout')

    def test_logout_successful(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Successfully logged out", response.data.get('detail'))
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_logout_invalid_token_or_already_logged_out(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.client.post(self.url)
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid token", response.data.get('detail'))

    def test_logout_unauthenticated(self):
        self.client.credentials()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserListViewSetTest(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='listuser1', first_name='List', last_name='UserOne',
                                              email='u1@example.com', password='password')
        self.user2 = User.objects.create_user(username='listuser2', first_name='Another', last_name='Person',
                                              email='u2@example.com', password='password')
        User.objects.create_user(username='inactiveuser', is_active=False, password='password')

        self.token = Token.objects.create(user=self.user1)
        self.url = reverse('userlist-list')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_list_users(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_users_search_username(self):
        response = self.client.get(self.url + '?search=listuser1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['username'], 'listuser1')

    def test_list_users_search_firstname(self):
        response = self.client.get(self.url + '?search=Another')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['username'], 'listuser2')

    def test_list_users_search_no_results(self):
        response = self.client.get(self.url + '?search=nonexistent')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_list_users_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)