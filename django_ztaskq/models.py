import datetime
import time
import sys
import traceback
import pickle
import json

from picklefield import PickledObjectField
from django.db.models import *

from .conf import settings, logger

class Status(object):
    """Enum-style class of possible task statuses."""
    QUEUED = u'Q'
    RUNNING = u'R'
    COMPLETED = u'C'
    FAILED = u'F'

# pretty forms for the admin interface
STATUS_CHOICES = (
    (Status.QUEUED, u'Queued'),
    (Status.RUNNING, u'Running'),
    (Status.COMPLETED, u'Completed'),
    (Status.FAILED, u'Failed'),
)

_func_cache = {} # could be a classwide "static" member (may have to override __new__)
class Task(Model):
    taskid = CharField(max_length=36, primary_key=True)
    
    function_name = CharField(max_length=255)
    args = PickledObjectField()
    kwargs = PickledObjectField()
    return_value = PickledObjectField(null=True)
    
    error = TextField(blank=True, null=True)
    
    queued = DateTimeField(blank=True, null=True)
    started = DateTimeField(blank=True, null=True)
    finished = DateTimeField(blank=True, null=True)
    
    status = CharField(max_length=1, choices=STATUS_CHOICES, 
        default=Status.QUEUED)
    
    def save(self, *args, **kwargs):
        if not self.queued:
            self.queued = datetime.datetime.utcnow()
        super(Task, self).save(*args, **kwargs)
    
    class Meta:
        db_table = 'django_ztaskq_task'
    
    @classmethod
    def run_task(cls, task_id):
        try:
            task = cls.objects.get(pk=task_id)
        except Exception, e:
            logger.info('Could not get task with id %s:\n%s' % (task_id, e))
            return
        task.run()
    
    def mark_running(self):
        self.status = Status.RUNNING
        self.started = datetime.datetime.utcnow()
        
        self.save()
    
    def mark_complete(self, success=True, delete=False, error_msg=''):
        """Mark the task as finished (success/failure)
        
        The error message is only used if success is False.
        
        """
        if delete:
            self.delete()
            return
        
        self.status = Status.COMPLETED if success else Status.FAILED
        if not success:
            self.error = error_msg
        self.finished = datetime.datetime.utcnow()
        
        self.save()
    
    def run(self):
        
        function_name = self.function_name
        args = self.args
        kwargs = self.kwargs
        
        self.mark_running()
        logger.info('Executing task function (%s)' % function_name)
        
        try:
            function = _func_cache[function_name]
        except KeyError:
            parts = function_name.split('.')
            module_name = '.'.join(parts[:-1])
            member_name = parts[-1]
            if not module_name in sys.modules:
                __import__(module_name)
            function = getattr(sys.modules[module_name], member_name)
            _func_cache[function_name] = function
        
        try:
            logger.info('Task.run is calling %r(%r, %r)' % (function, args, kwargs))
            return_value = function(*args, **kwargs)
            logger.info('Successfully finished the function call.')
        except Exception, e:
            traceback = sys.last_traceback if hasattr(sys, 'last_traceback') else 'no traceback available'
            self.mark_complete(success=False, error_msg=traceback)
            logger.error('Error calling %s. Details:\n%s' % (function_name, traceback))
            raise
        else:
            self.return_value = return_value
            self.save()
            self.mark_complete(success=True)
            logger.info('Called %s successfully' % function_name)

