# api/models.py
from django.db import models
#from django.contrib.auth.models import User
from django.utils import timezone


class User(models.Model):
    username = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=15,
                            choices=(("owner", "Business owner"),
                                     ("employee", "Employee"),
                                     ("topemployee", "Employee with elevated privileges"),
                                     ("admin", "Admin")),
                            default="employee")
    team = models.ForeignKey("Team", related_name="members", on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.username} ({self.email})"


class Team(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, related_name='owned_teams')

    def __str__(self):
        return f"{self.name} (Owner: {self.owner})"

class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, related_name='owned_projects', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    team = models.ForeignKey(Team, related_name="projects")
    def __str__(self):
        return self.name

class Task(models.Model):
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
    ]

    project = models.ForeignKey(Project, related_name='tasks', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')
    assignee = models.ForeignKey(User, related_name='assigned_tasks', on_delete=models.SET_NULL, null=True, blank=True)
    story_points = models.IntegerField(null=True, blank=True) # Also mentioned as part of task management
    deadline = models.DateField(null=True, blank=True) # Mentioned in task creation
    estimation_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Project: {self.project.name})"


class WorkLog(models.Model):
    user = models.ForeignKey(User, related_name='work_logs', on_delete=models.CASCADE)
    task = models.ForeignKey(Task, related_name='work_logs', on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey(Project, related_name='work_logs', on_delete=models.CASCADE, null=True, blank=True) # Якщо логуємо на рівні проекту
    date = models.DateField(default=timezone.now)
    hours_spent = models.DecimalField(max_digits=4, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.hours_spent}h on {self.date}"

    class Meta:
        ordering = ['-date', '-created_at']