#!/usr/bin/env python
from BaseRequestHandler import BaseRequestHandler
from google.appengine.ext.webapp.util import login_required
											
class SummaryHandler(BaseRequestHandler):
	@login_required
	def	get(self):
		self.updateproject()
		# generate output
		self.generate('summary', {
			'result': self.project.ResultData(),
			'groups': self.project.GroupDefList(),
			'currencies': self.project.CurrencyDefList()
		})
