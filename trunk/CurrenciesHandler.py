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
		self.updateproject()
		action = self.request.get('action','list')
		if action=='list':
			# add base currency of project
			self.response.out.write('<option value="%(value)s">%(name)s</option>' % 
				{'value':None, 'name':self.project.currency})
			# create a list of options against all accounts
			for a in self.project.currency_set:
				self.response.out.write('<option value="%(value)s">%(name)s</option>' % {
					'name':a.name, 
					'value':a.key()
				})
		
		elif action=='add':
			# add a new currency
			divisor=float(self.request.get('divisor', '1'))
			if divisor<0.01: raise Exception("Divisor must be greater or equal to 0.01")
			factor=float(self.request.get('factor', '1'))
			if factor<0.01: raise Exception("Factor must be greater or equal to 0.01")
			Currency(project=self.project, name=self.request.get('name'), factor=factor, divisor=divisor).put()
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
			divisor=float(self.request.get('divisor', '1'))
			if divisor<0.01: raise Exception("Divisor must be greater or equal to 0.01")
			factor=float(self.request.get('factor', '1'))
			if factor<0.01: raise Exception("Factor must be greater or equal to 0.01")
			c.name = self.request.get('name', c.name)
			c.divisor = divisor
			c.factor = factor
			c.put()
			# generate std output
			self.get()
			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
		
	def	get(self):
		self.updateproject()
		self.generate('currencies', {'currencies': self.project.currency_set })
