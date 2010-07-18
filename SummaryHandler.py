#!/usr/bin/env python
from BaseRequestHandler import BaseRequestHandler
import Security
											
class SummaryHandler(BaseRequestHandler):
	@Security.ProjectAccess(Security.Right_View)
	def	get(self):
		# calculate the result, this adds additional result fields to the self.project object
		self.project.CalculateResult();
		# generate output
		self.generate('summary');
