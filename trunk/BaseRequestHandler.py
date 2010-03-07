import os
import cgi
import datetime
import wsgiref.handlers
import StringIO
import random

from models import *

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template 
from google.appengine.ext.db import polymodel
from google.appengine.ext.db import BadKeyError
from google.appengine.ext.webapp.util import login_required
from datetime import datetime

# ******************************************************************************
# ** Base class for all handlers ***********************************************
# ******************************************************************************
class BaseRequestHandler(webapp.RequestHandler):
	"""Supplies a common template generation function.
	When you call generate(), we augment the template variables supplied with
	the current user in the 'user' variable and the current webapp request
	in the 'request' variable.
	"""
	def generate(self, template_name, template_values={}):
		values = {
		  'request': self.request,
		  'user': users.GetCurrentUser(),
		  'login_url': users.CreateLoginURL(self.request.uri),
		  'logout_url': users.CreateLogoutURL('/'),
		  'application_name': 'Urlaubsabrechnung',
		  'project': self.project,
		}
		if self.project:
			values['project_key'] = self.project.key()
		values.update(template_values)
		directory = os.path.dirname(__file__)
		path = os.path.join(directory, os.path.join('templates', template_name + '_en.html'))
		self.response.out.write(template.render(path, values, debug=True))
		
	"""(OBSOLETE) use @login instead! Checks, if a user is logged on, redirects to login page """
	def checklogin(self):
		if not users.GetCurrentUser():
			self.generate("login", { })
			return True
		return False
				
	def _handle_exception(self, exception, debug_mode):
		self.response.clear()
		self.response.set_status(400)
		self.response.out.write('<p>%(message)s</p>' % {'message':str(exception)})
	
	""" gets the project if applicable """
	def updateproject(self):
		k = self.request.get('project','')
		self.project = Project.get(k) if k!='' else None
