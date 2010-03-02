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
						
class JoinHandler(webapp.RequestHandler):
	@login_required
	def	get(self):
		try:  
			i = Invitation.get(self.request.get('invitation', ''))
			if i is None:
				self.redirect("/")
				return
			# only allow privilige increase, when the project and the code matches the stored Invitation instance
			if int(self.request.get('code', 0))==i.code and str(self.request.get('project', ''))==str(i.project.key()):
				# check for existiting access to project
				rights = ProjectRights.gql("WHERE user=:user and project=:project", user=users.get_current_user(), project=i.project).get()
				# edit rights
				if not rights:
					rights = ProjectRights(project=i.project, user=users.GetCurrentUser(), right=i.right)
				# possibly upgrade rights
				if rights.right<i.right:
					rights.right = i.right
				rights.put()
				# delete invitation
				i.delete()
			else:
				# invalid invitation
				raise Exception("Invalid invitation %(p1)s!=%(p2)s" % {'p1': self.request.get('project', ''), 'p2':i.project.key() } )
			# redirect to project summary, even if we can not increase priveliges
			self.redirect("/summary?project=%(project)s" % { 'project': i.project.key() } )
		except BadKeyError:
			# 
			self.redirect("/summary?project=%(project)s" % { 'project': self.request.get('project', 'invalid')} )
			return 
 