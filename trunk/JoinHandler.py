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
			i = Invitation.get(self.request.get('invitation', '0'))
			if i is None:
				self.redirect("/")
				return
			if int(self.request.get('code', 0))==i.code:
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
			# redirect to project list
			self.redirect("/")
		except BadKeyError:
			self.redirect("/")
			return 
