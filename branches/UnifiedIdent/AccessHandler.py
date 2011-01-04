#!/usr/bin/env python
import Security
import random
import models
import datetime
from BaseRequestHandler import BaseRequestHandler
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import mail
						
class AccessHandler(BaseRequestHandler):
	@Security.ProjectAccess(Security.Right_Manage)
	def	post(self):
		action = self.request.get('action', '')		
		if action == 'invite':
			if len(self.request.get('email', ''))<2:
				raise Exception("Specify email!")
			invitation = models.Invitation(				
				   project=self.token.project, 
				   user=users.User(email=self.request.get('email')), 
				   right=min(int(self.request.get('right')),self.token.right), 
				   code=random.randint(0, 2 << 31))
			invitation.put()
			message = mail.EmailMessage(
				sender=self.user.email(), 
				subject="Einladung " + self.token.DisplayName + " Urlaubsabrechung")
			message.to = invitation.user.email()
			message.html = self.render('invite_mail_en.html', { 'invitation': invitation })
			message.send()
		elif action == "create_ticket":
			if len(self.request.get('email', ''))<2:
				raise Exception("Specify email!")
			ticket = models.Ticket(
				project=self.token.project, 
				user=users.User(email=self.request.get('email')), 
				right=min(int(self.request.get('right')),self.token.right),
				expires=datetime.datetime.today() + datetime.timedelta(days=365), 
				code=random.randint(0, 2 << 31)
			)
			ticket.put()			
			message = mail.EmailMessage(
				sender=self.user.email(), 
				subject="Einladung " + self.token.DisplayName + " Urlaubsabrechung")
			message.to = ticket.user.email()
			message.html = self.render('ticket_mail_en.html', { 'ticket': ticket })
			message.send()
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
		# generate std output
		self.generate('access', {
				'rights': self.token.project.projectaccess_set,
				'invitations': self.token.project.invitation_set,
				'tickets': None,
		})
		
	@Security.ProjectAccess(Security.Right_Manage)
	def	get(self):
		action = self.request.get('action', '')		
		if action == "":
			pass
		elif action == "delete":
			entity = db.get(self.request.get('key', ''))
			if entity:
				if entity.project.key() != self.project.key():
					raise Exception("Access denied!")
				if entity.right>self.project.rights:
					raise Exception("Access denied!")
				if not (isinstance(entity, models.Invitation) or isinstance(entity, models.Ticket) or isinstance(entity, models.ProjectRights)):
					raise Exception("Invalid kind!")
				if self.security_key.key()==entity.key():
					raise Exception("Can't delete myself!")
				#raise Exception("delete %s" % entity.kind())
				entity.delete()
		else:
			raise Exception("Invalid action '%(action)s'!" % {'action':action})
		self.generate('access', {
				'rights': self.token.project.projectaccess_set,
				'invitations': self.project.invitation_set,
				'tickets': None,
		})		