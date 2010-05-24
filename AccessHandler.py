#!/usr/bin/env python
import random
from models import Invitation
from BaseRequestHandler import BaseRequestHandler
from google.appengine.api import users
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import mail
						
class AccessHandler(BaseRequestHandler):
	def	post(self):
		self.updateproject()
		action = self.request.get('action', 'list')
		if action == 'invite':	
			invitation = Invitation(project=self.project, user=users.User(email=self.request.get('email')), right=int(self.request.get('right')), code=random.randint(0, 2 << 31))
			invitation.put()
			message = mail.EmailMessage(sender=users.get_current_user().email(), subject="Einladung Urlaubsabrechnung")
			message.to = invitation.user.email()
			message.html = self.render('invite_mail_en.html', { 'invitation': invitation })
			message.send()
			# generate std output
			self.generate('access', {
					'rights': self.project.projectrights_set,
					'invitations': self.project.invitation_set,
			})
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
		
	@login_required
	def	get(self):
		self.updateproject()
		self.generate('access', {
				'rights': self.project.projectrights_set,
				'invitations': self.project.invitation_set,
		})