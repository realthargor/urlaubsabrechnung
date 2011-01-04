'''

Created on 18.07.2010

@author: Daniel
'''
from google.appengine.api import users
from datetime import datetime
import models

Right_None = 0
Right_Minimum = 1
Right_View = 100
Right_Edit = 200
Right_Manage = 500
Right_Owner = 1000
Right_Admin = 9999

def ProjectAccess(requested_permission):
	def wrapper(handler_method):
		def check_login(self, *args):
			try:
				try:
					self.token = models.ProjectAccess.GetFromToken(self.request.get('token', ''));
					if self.token==None and requested_permission>Right_None:
						# no project is specified redirect to main url, if any permissions where requested, but no user is logged on
						self.redirect("/")
						return
				except Exception:
					self.token = None
					self.generate("no_access", {
		  				'login_url': users.CreateLoginURL("/"),
					})
					return
				handler_method(self, *args)
			except (Exception), e:
				self.response.clear()
				self.response.set_status(400)
				self.response.out.write(e)
			pass
		return check_login
	return wrapper
