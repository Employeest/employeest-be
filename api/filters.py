import django_filters
from .models import Task


class TaskFilter(django_filters.FilterSet):
    deadline_after = django_filters.DateFilter(field_name='deadline', lookup_expr='gte')
    deadline_before = django_filters.DateFilter(field_name='deadline', lookup_expr='lte')

    project_name = django_filters.CharFilter(field_name='project__name', lookup_expr='icontains')

    class Meta:
        model = Task
        fields = {
            'project_id': ['exact'],
            'status': ['exact', 'in'],
            'assignee_id': ['exact', 'isnull'],
            'name': ['icontains'],
        }
