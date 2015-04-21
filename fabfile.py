from __future__ import with_statement
from fabric.api import *
from fabric.context_managers import shell_env

env.user = 'django'
env.hosts = ['hashmap.org']

def deploy():
	local('git add .')
	local('git commit -m "Fabric auto deploy"')
	local('git push origin master')
	code_dir = '/home/django/RSVPBot'
	with cd(code_dir):
		run('git pull')
