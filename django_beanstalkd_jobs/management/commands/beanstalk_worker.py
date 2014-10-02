import logging
from optparse import make_option
import os
import sys
import traceback

import time
from django.conf import settings
from django.core.management.base import NoArgsCommand
from django_beanstalkd_jobs import connect_beanstalkd, BeanstalkError
from beanstalkc import SocketError

from django.core.mail import mail_admins
from django_beanstalkd_jobs.models import JobRun
from django_beanstalkd_jobs.utils import set_current_job
from django.utils import timezone
import StringIO


logger = logging.getLogger('django_beanstalkd_jobs')
logger.addHandler(logging.StreamHandler())


class Command(NoArgsCommand):
    help = "Start a Beanstalk worker serving all registered Beanstalk jobs"
    __doc__ = help
    option_list = NoArgsCommand.option_list + (
        make_option('-w', '--workers', action='store', dest='worker_count',
                    default='1', help='Number of workers to spawn.'),
        make_option('-l', '--log-level', action='store', dest='log_level',
                    default='info', help='Log level of worker process (one of '
                    '"debug", "info", "warning", "error")'),
    )
    children = []  # list of worker processes
    jobs = {}

    def handle_noargs(self, **options):
        # set log level
        logger.setLevel(getattr(logging, options['log_level'].upper()))

        # find beanstalk job modules
        bs_modules = []
        for app in settings.INSTALLED_APPS:
            try:
                modname = "%s.beanstalk_jobs" % app
                __import__(modname)
                bs_modules.append(sys.modules[modname])
            except ImportError:
                pass
        if not bs_modules:
            logger.error("No beanstalk_jobs modules found!")
            return

        # find all jobs
        jobs = []
        for bs_module in bs_modules:
            try:
                jobs += bs_module.beanstalk_job_list
            except AttributeError:
                pass
        if not jobs:
            logger.error("No beanstalk jobs found!")
            return
        logger.info("Available jobs:")
        for job in jobs:
            # determine right name to register function with
            app = job.app
            jobname = job.__name__
            try:
                func = settings.BEANSTALK_JOB_NAME % {
                    'app': app,
                    'job': jobname,
                }
            except AttributeError:
                func = '%s.%s' % (app, jobname)
            self.jobs[func] = job
            logger.info("* %s" % func)

        # spawn all workers and register all jobs
        try:
            worker_count = int(options['worker_count'])
            assert(worker_count > 0)
        except (ValueError, AssertionError):
            worker_count = 1
        self.spawn_workers(worker_count)

        # start working
        logger.info("Starting to work... (press ^C to exit)")
        try:
            for child in self.children:
                os.waitpid(child, 0)
        except KeyboardInterrupt:
            sys.exit(0)

    def spawn_workers(self, worker_count):
        """
        Spawn as many workers as desired (at least 1).
        Accepts:
        - worker_count, positive int
        """
        # no need for forking if there's only one worker
        if worker_count == 1:
            return self.work()

        logger.info("Spawning %s worker(s)" % worker_count)
        # spawn children and make them work (hello, 19th century!)
        for i in range(worker_count):
            child = os.fork()
            if child:
                self.children.append(child)
                continue
            else:
                self.work()
                break

    def work(self):
        """children only: watch tubes for all jobs, start working"""
        try:

            while True:
                try:
                    # Reattempt Beanstalk connection if connection attempt
                    # fails or is dropped
                    beanstalk = connect_beanstalkd()
                    for job in self.jobs.keys():
                        beanstalk.watch(job)
                    beanstalk.ignore('default')

                    # Connected to Beanstalk queue, continually process jobs
                    # until an error occurs
                    self.process_jobs(beanstalk)

                except (BeanstalkError, SocketError) as e:
                    logger.info("Beanstalk connection error: " + str(e))
                    time.sleep(2.0)
                    logger.info("retrying Beanstalk connection...")

        except KeyboardInterrupt:
            sys.exit(0)

    def process_jobs(self, beanstalk):
        while True:
            logger.debug("Beanstalk connection established, waiting for jobs")
            job = beanstalk.reserve()
            job_name = job.stats()['tube']
            if job_name in self.jobs:
                self.launch_job(job, job_name)
            else:
                job.release()

    def launch_job(self, job, job_name):
        logger.debug("Calling %s with arg: %s" % (job_name, job.body))
        jobrun = JobRun()
        jobrun.name = job_name
        jobrun.parameter = job.body
        jobrun.jid = job.jid
        jobrun.status = 'running'
        jobrun.time_started = timezone.now()
        jobrun.save()
        set_current_job(jobrun)

        stdout = sys.stdout
        sys.stdout = StringIO.StringIO()
        stderr = sys.stderr
        sys.stderr = StringIO.StringIO()

        try:
            self.jobs[job_name](job.body)
        except Exception, e:
            tp, value, tb = sys.exc_info()
            error = 'Error while calling "%s" with arg "%s": %s' % (
                    job_name,
                    job.body,
                    e,
                )
            logger.error(error)
            logger.debug("%s:%s" % (tp.__name__, value))
            logger.debug("\n".join(traceback.format_tb(tb)))
            job.bury()

            jobrun.success = False
            jobrun.status = 'error'
            jobrun.exception = traceback.format_exc()
            mail_admins(error, jobrun.exception)
        else:
            job.delete()
            jobrun.success = True
            jobrun.status = 'done'

        jobrun.time_finished = timezone.now()
        jobrun.save()

        sys.stdout.flush()
        jobrun.stdout = sys.stdout.getvalue()
        sys.stdout = stdout

        sys.stderr.flush()
        jobrun.stderr = sys.stderr.getvalue()
        sys.stderr = stderr

        jobrun.save()
