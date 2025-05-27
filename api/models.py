from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date as datetime_date
from django.conf import settings

class User(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    ROLE_CHOICES = (
        ("owner", "Business owner"),
        ("employee", "Employee"),
        ("top_employee", "Employee with elevated privileges"),
        ("admin", "Admin")
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default="employee")

    def __str__(self):
        return f"{self.username} ({self.email})"

class Team(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, related_name='owned_teams', on_delete=models.CASCADE)
    members = models.ManyToManyField(User, through='TeamMember', related_name='member_of_teams')

    def __str__(self):
        return f"{self.name} (Owner: {self.owner})"

class TeamMember(models.Model):
    ROLE_IN_TEAM_CHOICES = [
        ('pm', 'Project manager'),
        ('member', 'Member'),
        ('lead', 'Team Lead'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_IN_TEAM_CHOICES, default='member')
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'team')
        ordering = ['team', 'user']

    def __str__(self):
        return f"{self.user.username} in {self.team.name} as {self.get_role_display()}"

class Project(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
    ]
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, related_name='owned_projects', on_delete=models.CASCADE)
    managers = models.ManyToManyField(User, related_name='managed_projects', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    team = models.ManyToManyField(Team, related_name="projects", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class Task(models.Model):
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('in_review', 'In Review'),
        ('DONE', 'Done'),
        ('CANCELLED', 'Cancelled'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    project = models.ForeignKey(Project, related_name='tasks', on_delete=models.CASCADE)
    parent_task = models.ForeignKey('self', null=True, blank=True, related_name='subtasks', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    assignee = models.ForeignKey(User, related_name='assigned_tasks', on_delete=models.SET_NULL, null=True, blank=True)
    story_points = models.IntegerField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    estimation_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Project: {self.project.name})"

    class Meta:
        ordering = ['-created_at']

class TaskComment(models.Model):
    task = models.ForeignKey(Task, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='task_comments', on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.task.name} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class TaskHistory(models.Model):
    task = models.ForeignKey(Task, related_name='history_logs', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='task_history_actions', on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    field_changed = models.CharField(max_length=100, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    change_description = models.CharField(max_length=255)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Task History"

    def __str__(self):
        if self.field_changed:
            return f"{self.task.name} - '{self.field_changed}' changed from '{self.old_value}' to '{self.new_value}' by {self.user.username if self.user else 'System'} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
        return f"{self.task.name} - {self.change_description} by {self.user.username if self.user else 'System'} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class WorkLog(models.Model):
    user = models.ForeignKey(User, related_name='work_logs', on_delete=models.CASCADE)
    task = models.ForeignKey(Task, related_name='work_logs', on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey(Project, related_name='work_logs', on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField(default=datetime_date.today)
    hours_spent = models.DecimalField(max_digits=4, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.hours_spent:.2f}h on {self.date}"

    class Meta:
        ordering = ['-date', '-created_at']
