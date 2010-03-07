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
		self.updateproject()
		action = self.request.get('action','list')
		if action=='invite':	
			i = Invitation(project=self.project, user=users.User(email=self.request.get('email')), right=int(self.request.get('right')), code=random.randint(0, 2<<31))
			i.put()
			message = mail.EmailMessage(sender=users.get_current_user().email(),
										subject="Invitation to Urlaubsabrechnung")
			message.to = i.user.email()
			message.body = "Hallo!\n\nDu bist eingeladen die Abrechnung fuer %(projectname)s anzusehen.\n\n" \
			"Bitte melde dich unter\nhttp://urlaubsabrechnung.appspot.com/join?project=%(project)s&invitation=%(invitation)s&code=%(code)d"\
			"\nmit einem google account an.!" % {
													'projectname':  self.project.name,
													'invitation':  i.key(),
													'project': self.project.key(),
													'code': i.code
												}
			message.send()
			# generate std output
			self.get()
			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
			
	def	get(self):
		self.updateproject()
		self.generate('access', {
				'rights': self.project.projectrights_set,
				'invitations': self.project.invitation_set,
			})
