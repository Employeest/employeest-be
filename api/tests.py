# employeest/employeest-be/employeest-be-072d382410c7e443938a6222569ff9013d9a2f12/api/tests.py
import requests # Should be at the top
from django.test import TestCase
from django.urls import reverse
# Ensure correct model import path if it's different
from .models import User, Team, Project, Task # Corrected: Removed WorkLog as it's not directly used in provided tests that were failing before
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch


class UserModelTest(TestCase):
    def setUp(self):
        # Creating a user first for Team's owner field
        self.team_main_owner = User.objects.create_user(username='teamowner', password='password')
        self.team = Team.objects.create(name='Test Team', owner=self.team_main_owner)

        self.user_admin = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='password123',
            role='admin',
            first_name='Admin',
            last_name='User',
            phone_number='1112223344'
        )

        self.user_employee = User.objects.create_user(
            username='employee_user',
            email='employee@example.com',
            password='password123',
            role='employee',
            first_name='Employee',
            last_name='User'
        )

        self.user_admin.team.add(self.team)

    def test_user_creation(self):
        self.assertEqual(self.user_admin.username, 'admin_user')
        self.assertEqual(self.user_admin.email, 'admin@example.com')
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


class TeamModelTest(TestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(username='team_owner_for_test', password='password')

    def test_team_creation(self):
        team = Team.objects.create(name='Another Team', owner=self.owner_user)
        self.assertEqual(team.name, 'Another Team')
        self.assertEqual(team.owner, self.owner_user)

    def test_team_str_representation(self):
        team = Team.objects.create(name='Marketing', owner=self.owner_user)
        expected_str = f"{team.name} (Owner: {self.owner_user})"
        self.assertEqual(str(team), expected_str)


class UserProfileViewTest(APITestCase): # Changed to APITestCase for self.client
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            first_name='Test',
            last_name='User',
            phone_number='1234567890',
            role='employee'
        )
        # self.client = APIClient() # APITestCase provides self.client
        self.client.login(username='testuser', password='testpassword')
        self.profile_url = reverse('user_profile')

    def test_user_profile_view_accessible_returns_json(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'], 'application/json')

        expected_data = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'phone_number': self.user.phone_number,
            'role': self.user.role,
        }
        # Using assertDictContainsSubset for flexibility if more fields are added by default
        self.assertJSONEqual(response.content.decode('utf-8'), expected_data)


    def test_user_profile_view_redirects_unauthenticated(self):
        self.client.logout() # Ensure user is logged out
        response = self.client.get(self.profile_url)
        # For API views, unauthenticated access usually results in 401 or 403,
        # not 302, unless specific redirection is set up.
        # The UserProfileView uses @method_decorator(login_required, name='dispatch')
        # which indeed redirects to LOGIN_URL if not authenticated.
        self.assertEqual(response.status_code, status.HTTP_302_FOUND) # default is /accounts/login/
        # Check if LOGIN_URL is set in settings, otherwise default is /accounts/login/
        self.assertTrue(response.url.startswith('/accounts/login/'))


class ProjectAPITests(APITestCase):
    def setUp(self):
        self.user_owner = User.objects.create_user(username='owner', password='password123', role='owner')
        self.user_employee = User.objects.create_user(username='employee', password='password123', role='employee')
        # self.client = APIClient() # APITestCase provides self.client

        # Authenticate as owner for most tests
        self.client.login(username='owner', password='password123')

        self.project1 = Project.objects.create(name='Project Alpha', description='Description Alpha', owner=self.user_owner)
        self.project2 = Project.objects.create(name='Project Beta', description='Description Beta', owner=self.user_owner)

    def test_create_project(self):
        url = reverse('project-list')
        data = {'name': 'Project Gamma', 'description': 'New project', 'owner_id': self.user_owner.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 3)
        self.assertEqual(Project.objects.get(name='Project Gamma').owner, self.user_owner)

    def test_list_projects(self):
        url = reverse('project-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # DRF list views often return paginated results.
        # Check 'count' for total or ensure results are what you expect.
        if 'results' in response.data: # Handling pagination
            self.assertEqual(len(response.data['results']), 2)
            self.assertEqual(response.data['count'], 2)
        else:
            self.assertEqual(len(response.data), 2)


    def test_retrieve_project(self):
        url = reverse('project-detail', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.project1.name)

    def test_update_project_owner(self):
        url = reverse('project-detail', kwargs={'pk': self.project1.pk})
        data = {'name': 'Project Alpha Updated', 'description': 'Updated Description', 'owner_id': self.user_owner.id}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.name, 'Project Alpha Updated')

    def test_update_project_not_owner(self):
        self.client.logout()
        self.client.login(username='employee', password='password123')
        url = reverse('project-detail', kwargs={'pk': self.project1.pk})
        data = {'name': 'Attempt Update Fail', 'description': 'Updated Description', 'owner_id': self.user_owner.id}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_project_owner(self):
        url = reverse('project-detail', kwargs={'pk': self.project1.pk})
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Project.objects.count(), 1)

    def test_delete_project_not_owner(self):
        self.client.logout()
        self.client.login(username='employee', password='password123')
        url = reverse('project-detail', kwargs={'pk': self.project1.pk})
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TaskAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='taskowner', password='password123', role='owner')
        self.assignee = User.objects.create_user(username='taskassignee', password='password123', role='employee')
        self.other_user = User.objects.create_user(username='otheruser', password='password123', role='employee')

        # self.client = APIClient() # APITestCase provides self.client
        self.client.login(username='taskowner', password='password123')

        self.project = Project.objects.create(name='Task Project', owner=self.owner)
        self.task1 = Task.objects.create(project=self.project, name='Task One', status='TODO', assignee=self.assignee, story_points=5)
        self.task2 = Task.objects.create(project=self.project, name='Task Two', status='IN_PROGRESS', assignee=self.owner)

    def test_create_task(self):
        url = reverse('task-list')
        data = {
            'name': 'Task Three',
            'project_id': self.project.id,
            'status': 'TODO',
            'assignee_id': self.assignee.id,
            'story_points': 3
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 3)

    def test_list_tasks(self):
        url = reverse('task-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if 'results' in response.data: # Handling pagination
            self.assertEqual(len(response.data['results']), 2)
            self.assertEqual(response.data['count'], 2)
        else:
            self.assertEqual(len(response.data), 2)

    def test_retrieve_task(self):
        url = reverse('task-detail', kwargs={'pk': self.task1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.task1.name)

    def test_update_task_owner_or_assignee(self):
        url = reverse('task-detail', kwargs={'pk': self.task1.pk})
        data = {'name': 'Task One Updated by Owner', 'status': 'DONE', 'project_id': self.project.id, 'assignee_id': self.assignee.id}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.name, 'Task One Updated by Owner')

        self.client.logout()
        self.client.login(username='taskassignee', password='password123')
        data = {'name': 'Task One Updated by Assignee', 'status': 'IN_PROGRESS', 'project_id': self.project.id, 'assignee_id': self.assignee.id}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.name, 'Task One Updated by Assignee')


    def test_update_task_not_owner_nor_assignee(self):
        self.client.logout()
        self.client.login(username='otheruser', password='password123')
        url = reverse('task-detail', kwargs={'pk': self.task1.pk})
        data = {'name': 'Attempt Update Fail', 'status': 'DONE', 'project_id': self.project.id, 'assignee_id': self.other_user.id}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_task_owner(self):
        url = reverse('task-detail', kwargs={'pk': self.task1.pk})
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Task.objects.count(), 1)

    def test_delete_task_assignee_permission_check(self):
        self.client.logout()
        self.client.login(username='taskassignee', password='password123')
        task_to_delete_by_assignee = Task.objects.create(project=self.project, name='Deletable by Assignee', assignee=self.assignee)
        url = reverse('task-detail', kwargs={'pk': task_to_delete_by_assignee.pk})
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_delete_task_not_owner_nor_assignee(self):
        self.client.logout()
        self.client.login(username='otheruser', password='password123')
        url = reverse('task-detail', kwargs={'pk': self.task2.pk})
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_start_progress_action(self):
        url = reverse('task-start-progress', kwargs={'pk': self.task1.pk})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.status, 'IN_PROGRESS')

    def test_task_mark_as_done_action(self):
        self.task2.status = 'IN_PROGRESS'
        self.task2.save()
        url = reverse('task-mark-as-done', kwargs={'pk': self.task2.pk})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task2.refresh_from_db()
        self.assertEqual(self.task2.status, 'DONE')
        self.assertIsNotNone(self.task2.updated_at)

    def test_task_filter_by_status(self):
        url = reverse('task-list')
        response = self.client.get(url + '?status=TODO', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        if 'results' in data: # handle pagination
            self.assertEqual(len(data['results']), 1)
            self.assertEqual(data['results'][0]['name'], self.task1.name)
        else:
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], self.task1.name)


    def test_task_filter_by_project_name(self):
        other_project_owner = User.objects.create_user(username='otherowner', password='password123')
        other_project = Project.objects.create(name='Other Project', owner=other_project_owner)
        # FIX: Removed 'owner=self.owner' as Task model does not have it.
        Task.objects.create(project=other_project, name='Task in Other Project', assignee=self.assignee)

        url = reverse('task-list')
        response = self.client.get(url + f'?project_name={self.project.name}', format='json') # Exact project name
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        expected_task_count = 2 # task1 and task2 are in 'Task Project'
        if 'results' in data: # handle pagination
            self.assertEqual(data['count'], expected_task_count)
        else:
            self.assertEqual(len(data), expected_task_count)


class ChartViewTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='chartowner', password='password123', role='owner')
        self.assignee = User.objects.create_user(username='chartassignee', password='password123', role='employee')
        # self.client = APIClient() # APITestCase provides self.client
        self.client.login(username='chartowner', password='password123')

        self.project = Project.objects.create(name='Chart Project', owner=self.owner)
        Task.objects.create(project=self.project, name='Task A', status='TODO', assignee=self.assignee, story_points=5, updated_at=timezone.now() - timedelta(days=70))
        Task.objects.create(project=self.project, name='Task B', status='IN_PROGRESS', assignee=self.owner, story_points=3, updated_at=timezone.now() - timedelta(days=60))
        Task.objects.create(project=self.project, name='Task C', status='DONE', assignee=self.assignee, story_points=8, updated_at=timezone.now() - timedelta(days=50))
        Task.objects.create(project=self.project, name='Task D', status='DONE', assignee=self.owner, story_points=2, updated_at=timezone.now() - timedelta(days=40))
        Task.objects.create(project=self.project, name='Task E', status='DONE', assignee=self.owner, story_points=1, updated_at=timezone.now() - timedelta(days=10))

        self.assignee_client = APIClient()
        self.assignee_client.login(username='chartassignee', password='password123')
        Task.objects.create(project=self.project, name='Assignee Task Done', status='DONE', assignee=self.assignee, updated_at=timezone.now() - timedelta(days=5))


    @patch('api.views.get_chart_url')
    def test_project_task_status_chart(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/piechart'
        # Assuming 'project-task-status-chart' is the correct name from url_name='task-status-chart' in @action
        url = reverse('project-task-status-chart', kwargs={'pk': self.project.pk})
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chart_url'], 'http://fakechart.url/piechart')
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(chart_config['options']['plugins']['title']['text'], f'Task Status Distribution for {self.project.name}')
        self.assertIn('DONE', chart_config['data']['labels'])
        self.assertIn('IN_PROGRESS', chart_config['data']['labels'])
        self.assertIn('TODO', chart_config['data']['labels'])
        done_index = chart_config['data']['labels'].index('DONE')
        # FIX: Changed expected count from 3 to 4
        self.assertEqual(chart_config['data']['datasets'][0]['data'][done_index], 4)


    @patch('api.views.get_chart_url')
    def test_project_velocity_chart(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/velocitychart'
        Task.objects.filter(project=self.project, name='Task C').update(updated_at=timezone.now() - timedelta(days=80), story_points=8)
        Task.objects.filter(project=self.project, name='Task D').update(updated_at=timezone.now() - timedelta(days=73), story_points=2)
        Task.objects.filter(project=self.project, name='Task E').update(updated_at=timezone.now() - timedelta(days=10), story_points=1)

        # QUICK FIX: Use the explicitly set url_name from views.py
        url = reverse('project-velocity-chart', kwargs={'pk': self.project.pk})
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chart_url'], 'http://fakechart.url/velocitychart')
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(chart_config['options']['plugins']['title']['text'], f'Velocity for Project: {self.project.name}')
        self.assertTrue(len(chart_config['data']['labels']) > 0)
        self.assertTrue(len(chart_config['data']['datasets'][0]['data']) > 0)
        self.assertEqual(sum(chart_config['data']['datasets'][0]['data']), 11)


    @patch('api.views.get_chart_url')
    def test_business_statistics_story_points_monthly(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/business_stats'
        # FIX: Removed 'owner=self.owner' as Task model does not have it.
        # Assigning to self.owner to match logic in view if it filters by owner implicitly or for consistency.
        Task.objects.create(project=self.project, name='Biz Task Old Month', status='DONE', assignee=self.owner, story_points=10, updated_at=timezone.now() - timedelta(days=35))

        url = reverse('business-stats-story-points')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chart_url'], 'http://fakechart.url/business_stats')
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(chart_config['options']['plugins']['title']['text'], 'Monthly Completed Story Points (Last Year)')
        self.assertTrue(len(chart_config['data']['labels']) > 0)
        # Task C (8), Task D (2), Task E (1), Biz Task Old Month (10) = 21
        self.assertEqual(sum(chart_config['data']['datasets'][0]['data']), 21)


    @patch('api.views.get_chart_url')
    def test_user_personal_task_stats(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/personal_stats'
        url = reverse('user-personal-task-stats')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chart_url'], 'http://fakechart.url/personal_stats')
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(chart_config['options']['plugins']['title']['text'], 'My Monthly Task Completions (Last Year)')
        self.assertTrue(len(chart_config['data']['labels']) > 0)
        # chartowner (self.owner) is assignee for Task D, Task E.
        self.assertEqual(sum(chart_config['data']['datasets'][0]['data']), 2)

        mock_get_chart_url.reset_mock()
        mock_get_chart_url.return_value = 'http://fakechart.url/assignee_personal_stats'
        Task.objects.create(project=self.project, name='Assignee Task Done 2', status='DONE', assignee=self.assignee, updated_at=timezone.now() - timedelta(days=3))
        response_assignee = self.assignee_client.get(url, format='json')
        self.assertEqual(response_assignee.status_code, status.HTTP_200_OK)
        args_assignee, _ = mock_get_chart_url.call_args
        chart_config_assignee = args_assignee[0]
        # self.assignee is assignee for Task A (TODO), Task C (DONE), 'Assignee Task Done' (DONE), 'Assignee Task Done 2' (DONE)
        # Total DONE by assignee = 3
        self.assertEqual(sum(chart_config_assignee['data']['datasets'][0]['data']), 3)


    @patch('api.views.get_chart_url')
    def test_project_task_status_chart_no_tasks(self, mock_get_chart_url):
        empty_project_owner = User.objects.create_user(username='emptyowner', password='password123')
        empty_project = Project.objects.create(name='Empty Project', owner=empty_project_owner)
        # Assuming 'project-task-status-chart' is correct name
        url = reverse('project-task-status-chart', kwargs={'pk': empty_project.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("No tasks found", response.data["message"])
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart_no_data(self, mock_get_chart_url):
        data_less_project_owner = User.objects.create_user(username='datalessowner', password='password123')
        data_less_project = Project.objects.create(name='Data Less Project', owner=data_less_project_owner)
        Task.objects.create(project=data_less_project, name='No SP Task', status='DONE', assignee=self.assignee, updated_at=timezone.now() - timedelta(days=10))
        Task.objects.create(project=data_less_project, name='Not Done Task', status='IN_PROGRESS', story_points=5, assignee=self.assignee, updated_at=timezone.now() - timedelta(days=10))

        # QUICK FIX: Use the explicitly set url_name from views.py
        url = reverse('project-velocity-chart', kwargs={'pk': data_less_project.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # This view returns 404 if not velocity_data
        self.assertIn("Not enough data", response.data["message"])
        mock_get_chart_url.assert_not_called()


    @patch('api.views.get_chart_url')
    def test_business_stats_no_data(self, mock_get_chart_url):
        Task.objects.filter(status='DONE', story_points__isnull=False).delete()
        url = reverse('business-stats-story-points')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("No completed tasks with story points found", response.data["message"])
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_user_personal_stats_no_data(self, mock_get_chart_url):
        Task.objects.filter(assignee=self.owner, status='DONE').delete()
        url = reverse('user-personal-task-stats')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("You have no completed tasks", response.data["message"])
        mock_get_chart_url.assert_not_called()

    @patch('api.quickchart_helper.requests.post')
    def test_get_chart_url_api_failure(self, mock_requests_post):
        mock_requests_post.side_effect = requests.RequestException("API Error")
        # Assuming 'project-task-status-chart' is correct name
        url = reverse('project-task-status-chart', kwargs={'pk': self.project.pk})
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['error'], 'Could not generate chart URL.')
        mock_requests_post.assert_called_once()