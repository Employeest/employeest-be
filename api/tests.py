import requests
from django.test import TestCase
from django.urls import reverse
from .models import User, Team, Project, Task, WorkLog
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.utils import timezone
from datetime import timedelta, date as datetime_date
from decimal import Decimal
from unittest.mock import patch


class UserModelTest(TestCase):
    def setUp(self):
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


class UserProfileViewTest(APITestCase):
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
        self.assertJSONEqual(response.content.decode('utf-8'), expected_data)

    def test_user_profile_view_redirects_unauthenticated(self):
        self.client.logout()
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response.url.startswith('/accounts/login/'))


class ProjectAPITests(APITestCase):
    def setUp(self):
        self.user_owner = User.objects.create_user(username='owner', password='password123', role='owner')
        self.user_employee = User.objects.create_user(username='employee', password='password123', role='employee')
        self.client.login(username='owner', password='password123')
        self.project1 = Project.objects.create(name='Project Alpha', description='Description Alpha',
                                               owner=self.user_owner)
        self.project2 = Project.objects.create(name='Project Beta', description='Description Beta',
                                               owner=self.user_owner)

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
        if 'results' in response.data:
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

    def test_partial_update_project_owner(self):
        url = reverse('project-detail', kwargs={'pk': self.project1.pk})
        data = {'description': 'Partially Updated Description'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.description, 'Partially Updated Description')
        self.assertEqual(self.project1.name, 'Project Alpha')

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

    @patch('api.views.get_chart_url')
    def test_project_task_status_chart_permission_denied_for_employee(self, mock_get_chart_url):
        self.client.logout()
        self.client.login(username='employee', password='password123')
        url = reverse('project-task-status-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart_permission_denied_for_employee(self, mock_get_chart_url):
        self.client.logout()
        self.client.login(username='employee', password='password123')
        url = reverse('project-velocity-chart', kwargs={'pk': self.project1.pk})
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_get_chart_url.assert_not_called()


class TaskAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='taskowner', password='password123', role='owner')
        self.assignee = User.objects.create_user(username='taskassignee', password='password123', role='employee')
        self.other_user = User.objects.create_user(username='otheruser', password='password123', role='employee')

        self.client.login(username='taskowner', password='password123')

        self.project = Project.objects.create(name='Task Project', owner=self.owner)
        self.task1 = Task.objects.create(project=self.project, name='Task One', status='TODO', assignee=self.assignee,
                                         story_points=5, deadline=datetime_date(2025, 12, 1))
        self.task2 = Task.objects.create(project=self.project, name='Task Two', status='IN_PROGRESS',
                                         assignee=self.owner, deadline=datetime_date(2025, 11, 1))

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
        if 'results' in response.data:
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
        data = {'name': 'Task One Updated by Owner', 'status': 'DONE', 'project_id': self.project.id,
                'assignee_id': self.assignee.id}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.name, 'Task One Updated by Owner')

        self.client.logout()
        self.client.login(username='taskassignee', password='password123')
        data = {'name': 'Task One Updated by Assignee', 'status': 'IN_PROGRESS', 'project_id': self.project.id,
                'assignee_id': self.assignee.id}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.name, 'Task One Updated by Assignee')

    def test_partial_update_task_owner_or_assignee(self):
        url = reverse('task-detail', kwargs={'pk': self.task1.pk})
        data = {'story_points': 10}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.story_points, 10)

        self.client.logout()
        self.client.login(username='taskassignee', password='password123')
        data = {'status': 'DONE'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.status, 'DONE')

    def test_update_task_not_owner_nor_assignee(self):
        self.client.logout()
        self.client.login(username='otheruser', password='password123')
        url = reverse('task-detail', kwargs={'pk': self.task1.pk})
        data = {'name': 'Attempt Update Fail', 'status': 'DONE', 'project_id': self.project.id,
                'assignee_id': self.other_user.id}
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
        task_to_delete_by_assignee = Task.objects.create(project=self.project, name='Deletable by Assignee',
                                                         assignee=self.assignee)
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

    def test_task_start_progress_action_already_in_progress(self):
        self.task2.status = 'IN_PROGRESS'
        self.task2.save()
        url = reverse('task-start-progress', kwargs={'pk': self.task2.pk})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_task_mark_as_done_action(self):
        self.task2.status = 'IN_PROGRESS'
        self.task2.save()
        url = reverse('task-mark-as-done', kwargs={'pk': self.task2.pk})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task2.refresh_from_db()
        self.assertEqual(self.task2.status, 'DONE')
        self.assertIsNotNone(self.task2.updated_at)

    def test_task_mark_as_done_action_from_todo(self):
        self.task1.status = 'TODO'
        self.task1.save()
        url = reverse('task-mark-as-done', kwargs={'pk': self.task1.pk})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_task_filter_by_status(self):
        url = reverse('task-list')
        response = self.client.get(url + '?status=TODO', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        if 'results' in data:
            self.assertEqual(len(data['results']), 1)
            self.assertEqual(data['results'][0]['name'], self.task1.name)
        else:
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], self.task1.name)

    def test_task_filter_by_project_name(self):
        other_project_owner = User.objects.create_user(username='otherowner', password='password123')
        other_project = Project.objects.create(name='Other Project', owner=other_project_owner)
        Task.objects.create(project=other_project, name='Task in Other Project', assignee=self.assignee)

        url = reverse('task-list')
        response = self.client.get(url + f'?project_name={self.project.name}', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        expected_task_count = 2
        if 'results' in data:
            self.assertEqual(data['count'], expected_task_count)
        else:
            self.assertEqual(len(data), expected_task_count)

    def test_task_filter_by_deadline_range(self):
        url = reverse('task-list')
        response_after = self.client.get(url + '?deadline_after=2025-11-15', format='json')
        self.assertEqual(response_after.status_code, status.HTTP_200_OK)
        data_after = response_after.json()
        if 'results' in data_after:
            self.assertEqual(data_after['count'], 1)
        else:
            self.assertEqual(len(data_after), 1)

        response_before = self.client.get(url + '?deadline_before=2025-11-15', format='json')
        self.assertEqual(response_before.status_code, status.HTTP_200_OK)
        data_before = response_before.json()
        if 'results' in data_before:
            self.assertEqual(data_before['count'], 1)
        else:
            self.assertEqual(len(data_before), 1)

        response_between = self.client.get(url + '?deadline_after=2025-10-01&deadline_before=2025-12-31', format='json')
        self.assertEqual(response_between.status_code, status.HTTP_200_OK)
        data_between = response_between.json()
        if 'results' in data_between:
            self.assertEqual(data_between['count'], 2)
        else:
            self.assertEqual(len(data_between), 2)


class ChartViewTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='chartowner', password='password123', role='owner')
        self.assignee = User.objects.create_user(username='chartassignee', password='password123', role='employee')
        self.client.login(username='chartowner', password='password123')

        self.project = Project.objects.create(name='Chart Project', owner=self.owner)
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

        self.assignee_client = APIClient()
        self.assignee_client.login(username='chartassignee', password='password123')
        Task.objects.create(project=self.project, name='Assignee Task Done', status='DONE', assignee=self.assignee,
                            updated_at=timezone.now() - timedelta(days=5))

    @patch('api.views.get_chart_url')
    def test_project_task_status_chart(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/piechart'
        url = reverse('project-task-status-chart', kwargs={'pk': self.project.pk})
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chart_url'], 'http://fakechart.url/piechart')
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(chart_config['options']['plugins']['title']['text'],
                         f'Task Status Distribution for {self.project.name}')
        self.assertIn('DONE', chart_config['data']['labels'])
        self.assertIn('IN_PROGRESS', chart_config['data']['labels'])
        self.assertIn('TODO', chart_config['data']['labels'])
        done_index = chart_config['data']['labels'].index('DONE')
        self.assertEqual(chart_config['data']['datasets'][0]['data'][done_index], 4)

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/velocitychart'
        Task.objects.filter(project=self.project, name='Task C').update(updated_at=timezone.now() - timedelta(days=80),
                                                                        story_points=8)
        Task.objects.filter(project=self.project, name='Task D').update(updated_at=timezone.now() - timedelta(days=73),
                                                                        story_points=2)
        Task.objects.filter(project=self.project, name='Task E').update(updated_at=timezone.now() - timedelta(days=10),
                                                                        story_points=1)

        url = reverse('project-velocity-chart', kwargs={'pk': self.project.pk})
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chart_url'], 'http://fakechart.url/velocitychart')
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(chart_config['options']['plugins']['title']['text'],
                         f'Velocity for Project: {self.project.name}')
        self.assertTrue(len(chart_config['data']['labels']) > 0)
        self.assertTrue(len(chart_config['data']['datasets'][0]['data']) > 0)
        self.assertEqual(sum(chart_config['data']['datasets'][0]['data']), 11)

    @patch('api.views.get_chart_url')
    def test_business_statistics_story_points_monthly(self, mock_get_chart_url):
        mock_get_chart_url.return_value = 'http://fakechart.url/business_stats'
        Task.objects.create(project=self.project, name='Biz Task Old Month', status='DONE', assignee=self.owner,
                            story_points=10, updated_at=timezone.now() - timedelta(days=35))

        url = reverse('business-stats-story-points')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chart_url'], 'http://fakechart.url/business_stats')
        mock_get_chart_url.assert_called_once()
        args, _ = mock_get_chart_url.call_args
        chart_config = args[0]
        self.assertEqual(chart_config['options']['plugins']['title']['text'],
                         'Monthly Completed Story Points (Last Year)')
        self.assertTrue(len(chart_config['data']['labels']) > 0)
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
        self.assertEqual(sum(chart_config['data']['datasets'][0]['data']), 2)

        mock_get_chart_url.reset_mock()
        mock_get_chart_url.return_value = 'http://fakechart.url/assignee_personal_stats'
        Task.objects.create(project=self.project, name='Assignee Task Done 2', status='DONE', assignee=self.assignee,
                            updated_at=timezone.now() - timedelta(days=3))
        response_assignee = self.assignee_client.get(url, format='json')
        self.assertEqual(response_assignee.status_code, status.HTTP_200_OK)
        args_assignee, _ = mock_get_chart_url.call_args
        chart_config_assignee = args_assignee[0]
        self.assertEqual(sum(chart_config_assignee['data']['datasets'][0]['data']), 3)

    @patch('api.views.get_chart_url')
    def test_project_task_status_chart_no_tasks(self, mock_get_chart_url):
        empty_project_owner = User.objects.create_user(username='emptyowner', password='password123')
        empty_project = Project.objects.create(name='Empty Project', owner=empty_project_owner)
        url = reverse('project-task-status-chart', kwargs={'pk': empty_project.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("No tasks found", response.data["message"])
        mock_get_chart_url.assert_not_called()

    @patch('api.views.get_chart_url')
    def test_project_velocity_chart_no_data(self, mock_get_chart_url):
        data_less_project_owner = User.objects.create_user(username='datalessowner', password='password123')
        data_less_project = Project.objects.create(name='Data Less Project', owner=data_less_project_owner)
        Task.objects.create(project=data_less_project, name='No SP Task', status='DONE', assignee=self.assignee,
                            updated_at=timezone.now() - timedelta(days=10))
        Task.objects.create(project=data_less_project, name='Not Done Task', status='IN_PROGRESS', story_points=5,
                            assignee=self.assignee, updated_at=timezone.now() - timedelta(days=10))

        url = reverse('project-velocity-chart', kwargs={'pk': data_less_project.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
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
        url = reverse('project-task-status-chart', kwargs={'pk': self.project.pk})
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['error'], 'Could not generate chart URL.')
        mock_requests_post.assert_called_once()


class WorkLogAPITests(APITestCase):
    def setUp(self):
        self.loguser1 = User.objects.create_user(username='loguser1', password='password123', role='employee')
        self.admin_user = User.objects.create_user(username='logadmin', password='password123', role='admin',
                                                   is_staff=True)
        self.project_owner = User.objects.create_user(username='logprojectowner', password='password123', role='owner')

        self.project = Project.objects.create(name='Logging Project', owner=self.project_owner)
        self.task = Task.objects.create(project=self.project, name='Logging Task', assignee=self.loguser1)

        self.worklog_user1_date = timezone.now().date() - timedelta(days=1)
        self.worklog_user1 = WorkLog.objects.create(user=self.loguser1, task=self.task, date=self.worklog_user1_date,
                                                    hours_spent='3.00', description="User1's old log")

        self.client.login(username='loguser1', password='password123')
        self.list_create_url = reverse('worklog-list')

    def test_create_worklog_for_task(self):
        log_date = timezone.now().date()
        data = {
            'task_id': self.task.id,
            'date': log_date.isoformat(),
            'hours_spent': '2.50',
            'description': 'Worked on task logging'
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WorkLog.objects.count(), 2)
        new_log = WorkLog.objects.latest('created_at')
        self.assertEqual(new_log.user, self.loguser1)
        self.assertEqual(new_log.task, self.task)

        self.assertEqual(new_log.hours_spent, Decimal(data['hours_spent']))
        self.assertEqual(new_log.date, log_date)

    def test_create_worklog_for_project(self):
        log_date = timezone.now().date()
        data = {
            'project_id': self.project.id,
            'date': log_date.isoformat(),
            'hours_spent': '1.00',
            'description': 'General project meeting'
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_log = WorkLog.objects.latest('created_at')
        self.assertEqual(new_log.project, self.project)
        self.assertIsNone(new_log.task)
        self.assertEqual(new_log.date, log_date)

    def test_create_worklog_unauthenticated(self):
        self.client.logout()
        data = {'task_id': self.task.id, 'date': timezone.now().date().isoformat(), 'hours_spent': '1.00'}
        response = self.client.post(self.list_create_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_worklog_for_task_and_project_fails(self):
        data = {
            'task_id': self.task.id,
            'project_id': self.project.id,
            'date': timezone.now().date().isoformat(),
            'hours_spent': '1.00',
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Work log cannot be associated with both a task and a project simultaneously.",
                      str(response.data))

    def test_create_worklog_for_neither_task_nor_project_fails(self):
        data = {
            'date': timezone.now().date().isoformat(),
            'hours_spent': '1.00',
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Work log must be associated with a task or a project.", str(response.data))

    def test_create_worklog_missing_hours_spent(self):
        data = {'task_id': self.task.id, 'date': timezone.now().date().isoformat()}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hours_spent', response.data)

    def test_create_worklog_missing_date(self):

        data = {'task_id': self.task.id, 'hours_spent': '1.50'}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_log = WorkLog.objects.latest('created_at')
        self.assertEqual(new_log.date, timezone.now().date())

    def test_list_own_worklogs(self):
        response = self.client.get(self.list_create_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        if 'results' in data:
            self.assertEqual(len(data['results']), 1)
            self.assertEqual(data['results'][0]['user']['id'], self.loguser1.id)
        else:
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['user']['id'], self.loguser1.id)

    def test_list_all_worklogs_as_admin(self):
        WorkLog.objects.create(user=self.admin_user, project=self.project, date=timezone.now().date(),
                               hours_spent='5.00')
        self.client.logout()
        self.client.login(username='logadmin', password='password123')
        response = self.client.get(self.list_create_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        if 'results' in data:
            self.assertEqual(data['count'], 2)
        else:
            self.assertEqual(len(data), 2)

    def test_retrieve_own_worklog(self):
        url = reverse('worklog-detail', kwargs={'pk': self.worklog_user1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.worklog_user1.id)

    def test_retrieve_others_worklog_by_user_fails(self):
        other_log = WorkLog.objects.create(user=self.admin_user, project=self.project, date=timezone.now().date(),
                                           hours_spent='1.0')
        url = reverse('worklog-detail', kwargs={'pk': other_log.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_others_worklog_by_admin_succeeds(self):
        self.client.logout()
        self.client.login(username='logadmin', password='password123')
        url = reverse('worklog-detail', kwargs={'pk': self.worklog_user1.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.worklog_user1.id)

    def test_update_own_worklog(self):
        url = reverse('worklog-detail', kwargs={'pk': self.worklog_user1.pk})

        put_data = {
            'hours_spent': '4.50',
            'description': 'Updated log',
            'date': self.worklog_user1_date.isoformat(),
            'task_id': self.task.id
        }
        response = self.client.put(url, put_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.worklog_user1.refresh_from_db()
        self.assertEqual(self.worklog_user1.hours_spent, Decimal(put_data['hours_spent']))
        self.assertEqual(self.worklog_user1.description, 'Updated log')

    def test_partial_update_own_worklog(self):
        url = reverse('worklog-detail', kwargs={'pk': self.worklog_user1.pk})
        patch_data = {'description': 'Partially updated log'}
        response = self.client.patch(url, patch_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, f"Response data: {response.data}")
        self.worklog_user1.refresh_from_db()
        self.assertEqual(self.worklog_user1.description, 'Partially updated log')

    def test_update_others_worklog_by_user_fails(self):
        other_log = WorkLog.objects.create(user=self.admin_user, project=self.project, date=timezone.now().date(),
                                           hours_spent='1.0')
        url = reverse('worklog-detail', kwargs={'pk': other_log.pk})
        data = {'hours_spent': '2.00', 'date': other_log.date.isoformat(), 'project_id': other_log.project.id}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_worklog(self):
        url = reverse('worklog-detail', kwargs={'pk': self.worklog_user1.pk})
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WorkLog.objects.filter(pk=self.worklog_user1.pk).exists())

    def test_delete_others_worklog_by_user_fails(self):
        other_log = WorkLog.objects.create(user=self.admin_user, project=self.project, date=timezone.now().date(),
                                           hours_spent='1.0')
        url = reverse('worklog-detail', kwargs={'pk': other_log.pk})
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(WorkLog.objects.filter(pk=other_log.pk).exists())
