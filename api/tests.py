from django.test import TestCase
from django.urls import reverse
from api.models import User, Team
from rest_framework import status


class UserModelTest(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name='Test Team',
                                        owner=User.objects.create_user(username='teamowner', password='password'))
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


class UserProfileViewTest(TestCase):
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

        self.assertIn('/accounts/login/', response.url)
