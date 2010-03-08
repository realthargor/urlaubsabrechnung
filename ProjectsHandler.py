#!/usr/bin/env python
import os
import cgi
import datetime
import wsgiref.handlers
import StringIO
import random

from models import *
from BaseRequestHandler import BaseRequestHandler

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template 
from google.appengine.ext.db import polymodel
from google.appengine.ext.db import BadKeyError
from google.appengine.ext.webapp.util import login_required
from datetime import datetime
from django.utils import simplejson as json
from google.appengine.api import mail
											
class ProjectsHandler(BaseRequestHandler):	
	@login_required
	def	get(self):
		if self.checklogin():
			return;
		self.updateproject()
		if users.is_current_user_admin():
			self.generate('projects', {
				'projects':  [{'name': project.name, 'rights':project.rights, 'id':project.key()} for project in Project.all()],
			})
		else:
			self.generate('projects', {
				'projects':  [{'name': right.project.name, 'rights':right.right, 'id':right.project.key()} for right in ProjectRights.gql("WHERE user=:user AND right>0", user=users.get_current_user())],
			})
	
	def	post(self):
		if not users.GetCurrentUser():
			self.response.out.write(users.CreateLoginURL("/"))
			return;
		self.updateproject()
		action = self.request.get('action','add')
		if action=='add':
			# create the project and return the new location to go to
			project = Project(name=self.request.get('name'), currency=self.request.get('currency'))
			project.put()
			# add access rights for this user to the new project
			rights = ProjectRights(project=project, user=users.GetCurrentUser(), right=255)
			rights.put()
			# redirect to summary
			self.response.out.write("/summary?project=%(key)s" % {'key':project.key()})
		elif action=='delete':
			# remove me from the projects right list
			project = Project.get(self.request.get('project',''))
			if (not project):
				raise Exception("Unknown project!")
			# check rights of current user for this project, and deny access if not permitable
			rights = ProjectRights.gql("WHERE user=:user and project=:project", user=users.get_current_user(), project=project).get()
			if rights:
				rights.delete()
			# redirect to my page
			self.response.out.write("/")
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
