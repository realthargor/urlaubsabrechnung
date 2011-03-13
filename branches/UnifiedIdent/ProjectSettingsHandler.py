#!/usr/bin/env python

import Security
from BaseRequestHandler import BaseRequestHandler

class ProjectSettingsHandler(BaseRequestHandler):
	@Security.ProjectAccess(Security.Right_Minimum)
	def	post(self):
		action = self.request.get('action', 'update')
		if action == 'update':
			updateProject = False
			# update the local project name
			if self.token:
				self.token.local_name = self.request.get('local_name', '')
				self.token.put()
			# update project currency
			if self.token.right >= Security.Right_Edit and len(self.request.get_all('project_currency'))>0:
				self.token.project.currency = self.request.get('project_currency')
				updateProject = True
			# update project name, if give and not empty
			if self.token.right >= Security.Right_Manage and len(self.request.get_all('project_name'))>0 and len(self.request.get('project_name', ''))>0:
				self.token.project.name = self.request.get('project_name')
				updateProject = True
			# update project
			if updateProject:
				self.token.project.put()
			# generate std output
			self.generate('projectsettings')
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
		
	@Security.ProjectAccess(Security.Right_Minimum)
	def	get(self):
		self.generate('projectsettings')
