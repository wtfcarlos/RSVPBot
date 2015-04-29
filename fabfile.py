from __future__ import with_statement
from fabric.api import *
from fabric.context_managers import shell_env

env.user = 'django'
env.hosts = ['insomn.io']

def deploy():
	code_dir = '/home/django/RSVPBot'
	with cd(code_dir):
		run('git pull')
		run('sudo service rsvp restart')
