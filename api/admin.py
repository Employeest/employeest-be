from django.contrib import admin
from .models import Project, Task, WorkLog, User


class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    fields = ('name', 'status', 'assignee', 'deadline', 'story_points')
    autocomplete_fields = ['assignee']
    show_change_link = True


class WorkLogInline(admin.TabularInline):
    model = WorkLog
    extra = 1
    fields = ('user', 'date', 'hours_spent', 'description')
    autocomplete_fields = ['user']

    show_change_link = True


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at', 'updated_at')
    list_filter = ('owner', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'owner')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [TaskInline, WorkLogInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'assignee', 'deadline', 'story_points', 'updated_at')
    list_filter = ('status', 'project', 'assignee', 'deadline', 'project__owner')
    search_fields = ('name', 'description', 'project__name', 'assignee__username')
    list_editable = ('status', 'assignee', 'deadline', 'story_points')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'deadline'
    list_per_page = 25
    autocomplete_fields = ['project', 'assignee']

    fieldsets = (
        (None, {
            'fields': ('project', 'name', 'description')
        }),
        ('Details', {
            'fields': ('status', 'assignee', 'story_points', 'deadline', 'estimation_hours')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.action(description='Mark selected tasks as DONE')
    def mark_as_done_action(self, request, queryset):
        queryset.update(status='DONE')
        self.message_user(request, f"{queryset.count()} tasks were successfully marked as DONE.")

    @admin.action(description='Mark selected tasks as IN_PROGRESS')
    def mark_as_in_progress_action(self, request, queryset):
        queryset.update(status='IN_PROGRESS')
        self.message_user(request, f"{queryset.count()} tasks were successfully marked as IN_PROGRESS.")

    actions = [mark_as_done_action, mark_as_in_progress_action]


@admin.register(WorkLog)
class WorkLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'task_display', 'project_display', 'date', 'hours_spent', 'created_at')
    list_filter = ('user', 'date', 'task__project')
    search_fields = ('user__username', 'task__name', 'project__name', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'date'
    list_per_page = 25
    autocomplete_fields = ['user', 'task', 'project']

    fieldsets = (
        (None, {
            'fields': ('user', ('task', 'project'), 'date', 'hours_spent', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Task')
    def task_display(self, obj):
        return obj.task.name if obj.task else "-"

    @admin.display(description='Project')
    def project_display(self, obj):
        return obj.project.name if obj.project else "-"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name', 'email', 'role']
    search_fields = ('username',)
