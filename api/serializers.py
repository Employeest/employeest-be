# api/serializers.py
from rest_framework import serializers
from .models import Project, Task, WorkLog, Team, User
#from django.contrib.auth.models import User

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class TeamSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'owner']

class TaskSimpleSerializer(serializers.ModelSerializer):
    assignee = UserSimpleSerializer(read_only=True, required=False)
    class Meta:
        model = Task
        fields = ['id', 'name', 'status', 'assignee', 'deadline']

class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSimpleSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='owner', write_only=True
    )
    tasks_count = serializers.SerializerMethodField()
    tasks = TaskSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'owner', 'owner_id',
            'created_at', 'updated_at',
            'tasks_count',
            'tasks'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner']

    def get_tasks_count(self, obj):
        return obj.tasks.count()


class TaskSerializer(serializers.ModelSerializer):
    assignee = UserSimpleSerializer(read_only=True, required=False)
    project_name = serializers.CharField(source='project.name', read_only=True)

    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assignee', write_only=True, allow_null=True, required=False
    )
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'description', 'status', 'story_points', 'deadline', 'estimation_hours',
            'project_id', 'project_name',
            'assignee_id', 'assignee',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'project_name', 'assignee']

    def validate_project_id(self, value):
        if not Project.objects.filter(pk=value.id).exists():
            raise serializers.ValidationError("Project does not exist.")
        return value

    def validate_assignee_id(self, value):
        if value and not User.objects.filter(pk=value.id).exists():
            raise serializers.ValidationError("Assignee (User) does not exist.")
        return value

class WorkLogSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True, default=serializers.CurrentUserDefault()
    )
    task_id = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(), source='task', write_only=True, allow_null=True, required=False
    )
    project_id = serializers.PrimaryKeyRelatedField(  # Якщо логування на рівні проекту
        queryset=Project.objects.all(), source='project', write_only=True, allow_null=True, required=False
    )

    class Meta:
        model = WorkLog
        fields = ['id', 'user', 'user_id', 'task', 'task_id', 'project', 'project_id', 'date', 'hours_spent',
                  'description', 'created_at']
        read_only_fields = ['id', 'user', 'created_at', 'task',
                            'project']

    def validate(self, data):
        if not data.get('task') and not data.get('project'):
            raise serializers.ValidationError("Work log must be associated with a task or a project.")
        if data.get('task') and data.get('project'):
            raise serializers.ValidationError(
                "Work log cannot be associated with both a task and a project simultaneously.")
        return data
