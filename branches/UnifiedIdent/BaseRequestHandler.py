import os
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp import template 

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
		self.response.out.write(self.render(template_name+'_en.html', template_values))
		pass
		
	"""Supplies a common template render function. """
	def render(self, template_name, template_values={}):
		if 'user' not in self.__dict__:
			self.user = users.GetCurrentUser()			
		if 'direct_link' not in self.__dict__:
			self.direct_link = False
		if 'project' not in self.__dict__:
			self.project = None
		if 'access_key' not in self.__dict__:
			self.access_key = None
		
		values = {
		  'direct_link': self.direct_link,
		  'access_key': self.access_key,
		  'request': self.request,
		  'user': self.user,
		  'login_url': users.CreateLoginURL(self.request.uri),
		  'logout_url': users.CreateLogoutURL('/'),
		  'project': self.project,
		}
		values.update(template_values)
		directory = os.path.dirname(__file__)
		path = os.path.join(directory, os.path.join('templates', template_name))
		return template.render(path, values, debug=True)
					
	def _handle_exception(self, exception, debug_mode):
		self.response.clear()
		self.response.set_status(400)
		self.response.out.write(exception.message)	