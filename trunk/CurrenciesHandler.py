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
								
class CurrenciesHandler(BaseRequestHandler):
	def	post(self):
		(project, right)=self.getandcheckproject(1)
		action = self.request.get('action','list')
		if action=='list':
			# add base currency of project
			self.response.out.write('<option value="%(value)s">%(name)s</option>' % {'value':None, 'name':project.currency})
			# create a list of options against all accounts
			for a in project.currency_set:
				self.response.out.write('<option value="%(value)s">%(name)s</option>' % {'name':a.name, 'value':a.key()})
		
		elif action=='add':
			# add a new currency
			Currency(project=project, name=self.request.get('name'), divisor=float(self.request.get('divisor', '1'))).put()
			# generate std output
			self.get()

		elif action=='delete':
			# delete existing currency
			c = Currency.get(self.request.get('key'))
			for t in c.transaction_set:
				t.delete()
			c.delete()
			# generate std output
			self.get()
			
		elif action=='update':
			# update existing currency
			c = Currency.get(self.request.get('key'))
			c.name = self.request.get('name', c.name)
			c.divisor = float(self.request.get('divisor', c.divisor))
			c.put()
			# generate std output
			self.get()
			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
		
	def	get(self):
		(project, right)=self.getandcheckproject(1)
		self.generate('currencies', {
			'project': project,
			'project_key': project.key(),
			'currencies': [
				{
					'name': currency.name,
					'divisor': currency.divisor,
					'key': currency.key(),
				} for currency in project.currency_set]
		})
