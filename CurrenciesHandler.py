#!/usr/bin/env python

import models
import Security
from BaseRequestHandler import BaseRequestHandler
								
class CurrenciesHandler(BaseRequestHandler):
	@Security.ProjectAccess(Security.Right_Edit)
	def	post(self):
		action = self.request.get('action', 'list')
		if action == 'list':
			# add base currency of project
			self.response.out.write('<option value="%(value)s">%(name)s</option>' % 
				{'value':None, 'name':self.project.currency})
			# create a list of options against all accounts
			for a in self.project.currency_set:
				self.response.out.write('<option value="%(value)s">%(name)s</option>' % {
					'name':a.name,
					'value':a.key()
				})
		
		elif action == 'add':
			# add a new currency
			divisor = float(self.request.get('divisor', '1'))
			if divisor < 0.01: raise Exception("Divisor must be greater or equal to 0.01")
			factor = float(self.request.get('factor', '1'))
			if factor < 0.01: raise Exception("Factor must be greater or equal to 0.01")
			models.Currency(project=self.project, name=self.request.get('name'), factor=factor, divisor=divisor).put()
			# generate std output
			self.generate('currencies', {'currencies': self.project.currency_set })

		elif action == 'delete':
			# delete existing currency
			c = models.Currency.get(self.request.get('key'))
			for t in c.transaction_set:
				t.delete()
			c.delete()
			# generate std output
			self.generate('currencies', {'currencies': self.project.currency_set })
			
		elif action == 'update':
			# update existing currency
			c = models.Currency.get(self.request.get('key'))
			divisor = float(self.request.get('divisor', '1'))
			if divisor < 0.01: raise Exception("Divisor must be greater or equal to 0.01")
			factor = float(self.request.get('factor', '1'))
			if factor < 0.01: raise Exception("Factor must be greater or equal to 0.01")
			c.name = self.request.get('name', c.name)
			c.divisor = divisor
			c.factor = factor
			c.put()
			# generate std output
			self.generate('currencies', {'currencies': self.project.currency_set })			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
		
	@Security.ProjectAccess(Security.Right_Edit)
	def	get(self):		
		self.generate('currencies', {'currencies': self.project.currency_set })
