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
		if 'project_list_enabled' not in self.__dict__:
			self.project_list_enabled = self.user!=None
		if 'project' not in self.__dict__:
			self.project = None
		if 'accesss_key' not in self.__dict__:
			self.accesss_key = None
		
		values = {
		  'project_list_enabled': self.project_list_enabled,
		  'accesss_key': self.accesss_key,
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
		self.response.out.write('<p>%(message)s</p>' % {'message':str(exception)})
	