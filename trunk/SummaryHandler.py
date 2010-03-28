#!/usr/bin/env python
from BaseRequestHandler import BaseRequestHandler
from google.appengine.ext.webapp.util import login_required
											
class SummaryHandler(BaseRequestHandler):
	@login_required
	def	get(self):
		self.updateproject()
		# calculate the result, this adds additional result fields to the self.project object
		self.project.CalculateResult();
		# generate output
		self.generate('summary');
