from rest_framework import serializers
from .models import Project, Task, WorkLog, Team, User


# api/serializers.py
from rest_framework import serializers
from .models import Project, Task, WorkLog, Team, User # User is already imported
from django.contrib.auth.password_validation import validate_password # For password strength
from django.core.exceptions import ValidationError


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)


    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name', 'phone_number')

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with that email address already exists.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', '')
            # role defaults to 'employee' as per your User model
        )
        # Note: Tokens are not automatically created here.
        # The user will need to log in to get a token.
        # Or, you can explicitly create one: Token.objects.create(user=user)
        return user

class AssigneeUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'display_name']

    def get_display_name(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name} ({obj.username})"
        return obj.username

class TeamSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'owner']

class TeamDetailSerializer(serializers.ModelSerializer):
    owner = UserSimpleSerializer(read_only=True)
    members = UserSimpleSerializer(many=True, read_only=True) # Crucial: list of members

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'owner', 'members']


class TaskSimpleSerializer(serializers.ModelSerializer):
    assignee = UserSimpleSerializer(read_only=True, required=False)

    class Meta:
        model = Task
        fields = ['id', 'name', 'status', 'assignee', 'deadline']


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSimpleSerializer(read_only=True) # Correct for displaying owner information

    # Make owner_id not required for input, as perform_create handles it.
    # It's still write_only, meaning if provided, it would attempt to set the 'owner' field.
    # But since perform_create overrides it, making it not required is key.
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='owner',
        write_only=True,
        required=False, # <--- KEY CHANGE: Make it not required
        allow_null=True  # <--- Also good to add if it can be null before perform_create sets it
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
        # 'owner' field is correctly read-only for output as defined by UserSimpleSerializer(read_only=True)
        # For input, owner_id is handled.
        read_only_fields = ['id', 'created_at', 'updated_at'] # 'owner' is handled by its own read_only=True

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
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True, allow_null=True, required=False
    )

    class Meta:
        model = WorkLog
        fields = ['id', 'user', 'user_id', 'task', 'task_id', 'project', 'project_id', 'date', 'hours_spent',
                  'description', 'created_at']
        read_only_fields = ['id', 'user', 'created_at', 'task',
                            'project']

    def validate(self, data):
        instance = self.instance

        effective_task = data.get('task', instance.task if instance else None)
        if 'task' in data and data['task'] is None:
            effective_task = None

        effective_project = data.get('project', instance.project if instance else None)
        if 'project' in data and data['project'] is None:
            effective_project = None

        if effective_task and effective_project:
            raise serializers.ValidationError(
                "Work log cannot be associated with both a task and a project simultaneously."
            )
        if not effective_task and not effective_project:
            raise serializers.ValidationError(
                "Work log must be associated with a task or a project."
            )
        return data
