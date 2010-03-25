#!/usr/bin/env python
from BaseRequestHandler import BaseRequestHandler
from google.appengine.ext.webapp.util import login_required
											
class SummaryHandler(BaseRequestHandler):
	@login_required
	def	get(self):
		self.updateproject()
		# calculate the result
		self.project.CalculateResult();
		# generate output
		self.generate('summary', {
			'groups': self.project.GroupDefList(),
			'currencies': self.project.CurrencyDefList()
		})
