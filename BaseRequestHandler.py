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
		  'logout_url': users.CreateLogoutURL(self.request.uri),
		  'application_name': 'Urlaubsabrechnung',
		}
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
	
	# checks, if the user has at least the required rights
	# to the given project
	# throws an exception, if the rights are not sufficent
	# returns a tuple with actual project and the  rights otherwise	
	def getandcheckproject(self, required_rights):
		try:
			project = Project.get(self.request.get('project',''))
			if (not project):
				raise Exception("Unknown project!")
			# check rights of current user for this project, and deny access if not permitable
			rights = ProjectRights.gql("WHERE user=:user and project=:project", user=users.get_current_user(), project=project).get()
			if (not rights) or (rights.right<required_rights):
				raise Exception("Access denied!")
			return (project, rights.right)
		except BadKeyError:
			self.response.clear()
			self.redirect("/")
