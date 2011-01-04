#!/usr/bin/env python
from models import Project, ProjectAccess, ProjectAccessAuthenticated
from google.appengine.api import users
from BaseRequestHandler import BaseRequestHandler
import Security

from google.appengine.ext.webapp.util import login_required

class ProjectsHandler(BaseRequestHandler):
	@Security.ProjectAccess(Security.Right_None)
	def	get(self):
		self.generate('projects', {
			'tokens':  ProjectAccess.ListUserProjects(),
			'adminTokens': ProjectAccess.ListProjectsAsAdmin(),
		})

	@Security.ProjectAccess(Security.Right_None)
	def	post(self):
		action = self.request.get('action', 'add')
		if action == 'add':
			if len(self.request.get('name'))<2:
				raise Exception("project name must be at least 2 characters long")
			if len(self.request.get('currency'))<1:
				raise Exception("project currency must be at least one character long")
			# create the project and return the new location to go to
			project = Project(name=self.request.get('name'), currency=self.request.get('currency'))
			project.put()
			# add access rights for this user to the new project
			token = ProjectAccessAuthenticated(project=project, user=users.get_current_user(), right=Security.Right_Owner, local_name="")
			token.put()
			# redirect to summary
			self.response.out.write("/summary?token=%(token)s" % {'token':token.Token()})
		elif action == 'delete':
			# remove me from the projects right list
			project = Project.get(self.request.get('project', ''))
			if (not token):
				raise Exception("Unknown project!")
			# check rights of current user for this project, and deny access if not permitable
			token = ProjectAccessAuthenticated.gql("WHERE user=:user and project=:project", user=users.get_current_user(), project=project).get()
			if token:
				token.delete()
			# redirect to my page
			self.response.out.write("/")
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
