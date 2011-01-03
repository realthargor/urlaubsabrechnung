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
			if self.project.settings:
				self.project.local_name = self.request.get('local_name', '')
				self.project.settings.local_name = self.project.local_name
				self.project.settings.put()
			# update project currency
			if self.project.rights >= Security.Right_Edit and len(self.request.get_all('project_currency'))>0:
				self.project.currency = self.request.get('project_currency')
				updateProject = True
			# update project name, if give and not empty
			if self.project.rights >= Security.Right_Manage and len(self.request.get_all('project_name'))>0 and len(self.request.get('project_name', ''))>0:
				self.project.name = self.request.get('project_name')
				updateProject = True
			# update project
			if updateProject:
				self.project.put()
			# update display name
			self.project.display_name = self.project.local_name if self.project.local_name and self.project.local_name != '' else self.project.name
			# generate std output			
			self.generate('projectsettings')			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
		
	@Security.ProjectAccess(Security.Right_Minimum)
	def	get(self):		
		self.generate('projectsettings')
