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
						
class AccessHandler(BaseRequestHandler):
	def	post(self):
		(project, right)=self.getandcheckproject(1)
		action = self.request.get('action','list')
		if action=='invite':	
			i = Invitation(project=project, user=users.User(email=self.request.get('email')), right=int(self.request.get('right')), code=random.randint(0, 2<<31))
			i.put()
			message = mail.EmailMessage(sender=users.get_current_user().email(),
										subject="Invitation to Urlaubsabrechnung")
			message.to = i.user.email()
			message.body = "Hallo!\n\nDu bist eingeladen die Abrechnung fuer %(projectname)s anzusehen.\n\n" \
			"Bitte melde dich unter\nhttp://urlaubsabrechnung.appspot.com/join?project=%(project)s&invitation=%(invitation)s&code=%(code)d"\
			"\nmit einem google account an.!" % {
													'projectname':  project.name,
													'invitation':  i.key(),
													'project': project.key(),
													'code': i.code
												}
			message.send()
			# generate std output
			self.get()
			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
			
	def	get(self):
		(project, right)=self.getandcheckproject(1)
		self.generate('access', {
			'project': project,
			'project_key': project.key(),
			'rights': [
				{
					'user': right.user,
					'right': right.right,
					'key': right.key(),
				} for right in project.projectrights_set
			],
			'invitations': [
				{
					'user': invitation.user,
					'right': invitation.right,
					'created': invitation.created,
					'key': invitation.key(),
				} for invitation in project.invitation_set
			]
		})
