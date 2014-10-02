from django.contrib import admin

from models import Job, JobRun

from django.forms import TextInput, Textarea
from django.db import models


class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'last_run_time', 'last_run_status',
                    'next_run_time')

admin.site.register(Job, JobAdmin)


class JobRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'success', 'status', 'time_started',
                    'time_finished',)
    list_display_links = ('name', 'status', 'time_started', 'time_finished')
    list_filter = ('success', 'status',)
    search_fields = ('name',)

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '100'})},
        models.TextField: {'widget': Textarea(attrs={'rows': 16,
                                                     'cols': 200})},
    }

admin.site.register(JobRun, JobRunAdmin)
