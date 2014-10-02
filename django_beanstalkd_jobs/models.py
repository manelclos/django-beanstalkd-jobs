from django.db import models
import json

STATUS_TYPE = (
    ('ready', 'Ready'),
    ('running', 'Running'),
    ('error', 'Error'),
    ('done', 'Done'),
)


class Job(models.Model):
    name = models.CharField(max_length=100, help_text='app.jobname')
    parameter = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=100, null=True, blank=True,
                                   help_text='Human description')
    next_run_time = models.DateTimeField(null=True, blank=True)
    last_run_time = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(max_length=100, null=True, blank=True)
    last_success_run = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        if self.description:
            s = '%s (%s)' % (self.description, self.name)
        else:
            s = "%s" % (self.name)
        return s


class SpyDict(dict):
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        if hasattr(self, 'callback'):
            self.callback()

    def set_callback(self, callback):
        self.callback = callback


class JobRun(models.Model):
    job = models.ForeignKey(Job, related_name="runs", null=True, blank=True)
    name = models.CharField(max_length=100, help_text='app.jobname')
    parameter = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=100, null=True, blank=True,
                                   help_text='Human description')
    jid = models.IntegerField(null=True, blank=True,
                              help_text='Beanstalkd job id')
    pid = models.IntegerField(null=True, blank=True,
                              help_text='System process id')
    success = models.NullBooleanField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_TYPE,
                              null=True, blank=True)
    time_started = models.DateTimeField(null=True, blank=True)
    time_finished = models.DateTimeField(null=True, blank=True)
    meta_json = models.TextField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    exception = models.TextField(null=True, blank=True)

    meta = SpyDict()

    def meta_callback(self):
        """
        encode current meta content and save it in meta_json field
        """
        self.meta_json = json.dumps(self.meta)
        self.save()

    def __init__(self, *args, **kwargs):
        """
        on init, try to load meta_json field content into meta dict
        """
        super(JobRun, self).__init__(*args, **kwargs)
        try:
            data = json.loads(self.meta_json)
            self.meta.update(data)
        except:
            pass
        self.meta.set_callback(self.meta_callback)

    def __unicode__(self):
        if self.description:
            s = '%s (%s)' % (self.description, self.name)
        else:
            s = "%s" % (self.name)
        return s
