#!/usr/bin/env python
import Security
import random
import models
import datetime
from BaseRequestHandler import BaseRequestHandler
from google.appengine.api import users
from google.appengine.api import mail
						
class AccessHandler(BaseRequestHandler):
	@Security.ProjectAccess(Security.Right_Manage)
	def	post(self):
		action = self.request.get('action', '')
		if action == 'invite':
			invitation = models.Invitation(
				   project=self.project, 
				   user=users.User(email=self.request.get('email')), 
				   right=min(int(self.request.get('right')),self.project.rights), 
				   code=random.randint(0, 2 << 31))
			invitation.put()
			message = mail.EmailMessage(
				sender=self.user.email(), 
				subject="Einladung " + self.project.display_name + " Urlaubsabrechung")
			message.to = invitation.user.email()
			message.html = self.render('invite_mail_en.html', { 'invitation': invitation })
			message.send()
		elif action == "create_ticket":
			ticket = models.Ticket(
				project=self.project, 
				user=users.User(email=self.request.get('email')), 
				right=min(int(self.request.get('right')),self.project.rights),
				expires=datetime.datetime.today() + datetime.timedelta(days=365), 
				code=random.randint(0, 2 << 31)
			)
			ticket.put()			
			message = mail.EmailMessage(
				sender=self.user.email(), 
				subject="Einladung " + self.project.display_name + " Urlaubsabrechung")
			message.to = ticket.user.email()
			message.html = self.render('ticket_mail_en.html', { 'ticket': ticket })
			message.send()
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
		# generate std output
		self.generate('access', {
				'rights': self.project.projectrights_set,
				'invitations': self.project.invitation_set,
				'tickets': self.project.ticket_set,
		})
		
	@Security.ProjectAccess(Security.Right_Manage)
	def	get(self):
		if self.request.get('action', '') == 'delete_ticket' and self.request.get('ticket', '')!='':
			ticket = models.Ticket.get(self.request.get('ticket', ''))
			if ticket.project.key()!=self.project.key():
				raise Exception("Unauthorized access!")
			ticket.delete()
		self.generate('access', {
				'rights': self.project.projectrights_set,
				'invitations': self.project.invitation_set,
				'tickets': self.project.ticket_set,
		})