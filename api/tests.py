from django.test import TestCase
from django.urls import reverse
from api.models import User, Tea

class UserModelTest(TestCase):
    def setUp(self): # setUp for tests
        self.team = Team.objects.create(name='Test Team')
        self.user_admin = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='password123',
            role='admin',
            first_name='Admin',
            last_name='User',
            phone_number='1112223344'
        )
        self.user_admin.team.add(self.team)

        self.user_employee = User.objects.create_user(
            username='employee_user',
            email='employee@example.com',
            password='password123',
            role='employee',
            first_name='Employee',
            last_name='User'
        )

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
    def test_team_creation(self):
        team = Team.objects.create(name='Another Team')
        self.assertEqual(team.name, 'Another Team')

    def test_team_str_representation(self):
        team = Team.objects.create(name='Marketing')
        self.assertEqual(str(team), 'Marketing')


class UserProfileViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')

    def test_user_profile_view_accessible(self):
        response = self.client.get(reverse('user_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'my_app/user_profile.html')
        self.assertEqual(response.context['user'], self.user)

    def test_user_profile_view_redirects_unauthenticated(self):
        self.client.logout() # Виходимо з системи
        response = self.client.get(reverse('user_profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)