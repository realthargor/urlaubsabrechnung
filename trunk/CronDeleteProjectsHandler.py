#!/usr/bin/env python
from models import Project, ProjectRights
from google.appengine.api import users
from BaseRequestHandler import BaseRequestHandler
import Security
from google.appengine.ext.webapp.util import login_required

class CronDeleteProjectsHandler(BaseRequestHandler):	
	def	get(self):		
		self.response.out.write("<html><body><h1>deleting abandoned projects</h1><ol>")
		# iterate over list of projects no one has access rights anymore
		for p in [p for p in Project.all() if len([r for r in p.projectrights_set])==0]:
			self.response.out.write("<li>Project: %s<ul>" % p.name)			
			for t in p.transaction_set:
				self.response.out.write("<li>transaction</li>")
				t.delete()
			for a in p.person_set:
				self.response.out.write("<li>Account: %s<ul>" % a.name)
				for m in a.member_set:
					if m.group.key()!=a.key():
						self.response.out.write("<li>Membership: %s</li>" % m.group.name)
						m.delete()
				a.delete()
				self.response.out.write("</ul></li>")
			for c in p.currency_set:
				self.response.out.write("<li>Currency: %s</li>" % c.name)
				c.delete()
			for t in p.ticket_set:
				self.response.out.write("<li>Ticket: %s</li>" % t.user)
				t.delete()
			for i in p.invitation_set:
				self.response.out.write("<li>Invitation: %s</li>" % i.user)
				i.delete()
			self.response.out.write("</ul></li>")
			p.delete()
		self.response.out.write("</ol></body></html>")