from rest_framework import serializers
from .models import Project, Task, WorkLog, Team, User, TeamMember, TaskComment, TaskHistory
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name', 'phone_number', 'role')
        extra_kwargs = {
            'role': {'read_only': True}
        }

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
        )
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


class TeamMemberSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)
    team_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = TeamMember
        fields = ['id', 'user', 'user_id', 'team', 'team_id', 'role', 'date_joined']
        read_only_fields = ['team', 'date_joined']

    def create(self, validated_data):
        team_id = self.context['view'].kwargs.get('team_pk')
        validated_data['team_id'] = team_id
        try:
            return super().create(validated_data)
        except Exception as e:  # IntegrityError for unique_together
            raise serializers.ValidationError(str(e))


class TeamSerializer(serializers.ModelSerializer):
    owner = UserSimpleSerializer(read_only=True)
    memberships = TeamMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'owner', 'memberships']


class TeamDetailSerializer(serializers.ModelSerializer):
    owner = UserSimpleSerializer(read_only=True)
    memberships = TeamMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'owner', 'memberships']


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSimpleSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='owner',
        write_only=True,
        required=False,
        allow_null=True
    )
    managers = UserSimpleSerializer(many=True, read_only=True)
    manager_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='managers',
        write_only=True,
        many=True,
        required=False
    )
    tasks_count = serializers.SerializerMethodField()
    team_details = TeamSerializer(source='team', many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'owner', 'owner_id',
            'managers', 'manager_ids', 'status',
            'created_at', 'updated_at',
            'tasks_count', 'team', 'team_details'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'tasks_count', 'owner', 'team_details']

    def get_tasks_count(self, obj):
        return obj.tasks.count()


class TaskCommentSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'user', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['task', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['task'] = self.context['view'].get_task_object()
        return super().create(validated_data)


class TaskHistorySerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = TaskHistory
        fields = ['id', 'task', 'user', 'timestamp', 'field_changed', 'old_value', 'new_value', 'change_description']


class TaskSerializer(serializers.ModelSerializer):
    assignee = UserSimpleSerializer(read_only=True, required=False)
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_status = serializers.CharField(source='project.status', read_only=True)
    subtasks = serializers.SerializerMethodField(read_only=True)
    comments_count = serializers.SerializerMethodField(read_only=True)

    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assignee', write_only=True, allow_null=True, required=False
    )
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), source='project', write_only=True
    )
    parent_task_id = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(), source='parent_task', write_only=True, allow_null=True, required=False
    )

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'description', 'status', 'priority', 'story_points', 'deadline', 'estimation_hours',
            'project_id', 'project_name', 'project_status',
            'assignee_id', 'assignee',
            'parent_task_id', 'parent_task', 'subtasks',
            'comments_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'project_name', 'project_status', 'assignee',
                            'parent_task', 'subtasks', 'comments_count']

    def get_subtasks(self, obj):
        subtasks = Task.objects.filter(parent_task=obj)
        return TaskSimpleSerializer(subtasks, many=True, context=self.context).data

    def get_comments_count(self, obj):
        return obj.comments.count()

    def validate_project_id(self, value):
        if not Project.objects.filter(pk=value.id).exists():
            raise serializers.ValidationError("Project does not exist.")
        return value

    def validate_assignee_id(self, value):
        if value and not User.objects.filter(pk=value.id).exists():
            raise serializers.ValidationError("Assignee (User) does not exist.")
        return value

    def validate_parent_task_id(self, value):
        if value and not Task.objects.filter(pk=value.id).exists():
            raise serializers.ValidationError("Parent task does not exist.")
        if value and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError("A task cannot be its own parent.")
        return value

    def _log_history(self, instance, old_data, user):
        changes = []
        for field, new_value in self.validated_data.items():
            if field in ['assignee_id', 'project_id', 'parent_task_id']:
                old_fk_id = old_data.get(field + '_id', None)
                new_fk_id = new_value.id if new_value else None
                if old_fk_id != new_fk_id:
                    changes.append({
                        'field_changed': field.replace('_id', ''),
                        'old_value': str(
                            User.objects.get(id=old_fk_id) if field == 'assignee_id' and old_fk_id else old_fk_id),
                        'new_value': str(new_value),
                        'change_description': f"{field.replace('_id', '').capitalize()} changed."
                    })
            elif field not in ['updated_at', 'created_at'] and hasattr(instance, field):
                old_value = old_data.get(field, getattr(instance, field))
                if old_value != new_value:
                    changes.append({
                        'field_changed': field,
                        'old_value': str(old_value),
                        'new_value': str(new_value),
                        'change_description': f"{field.capitalize()} changed to '{new_value}'."
                    })

        for change in changes:
            TaskHistory.objects.create(task=instance, user=user, **change)

    def create(self, validated_data):
        instance = super().create(validated_data)
        TaskHistory.objects.create(task=instance, user=self.context['request'].user,
                                   change_description=f"Task '{instance.name}' created.")
        return instance

    def update(self, instance, validated_data):
        old_data = TaskSerializer(instance).data

        old_fk_data = {
            'assignee_id': instance.assignee_id,
            'project_id': instance.project_id,
            'parent_task_id': instance.parent_task_id,
        }
        old_data.update(old_fk_data)

        updated_instance = super().update(instance, validated_data)
        self._log_history(updated_instance, old_data, self.context['request'].user)
        return updated_instance


class TaskSimpleSerializer(serializers.ModelSerializer):
    assignee = UserSimpleSerializer(read_only=True, required=False)

    class Meta:
        model = Task
        fields = ['id', 'name', 'status', 'priority', 'assignee', 'deadline']


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
