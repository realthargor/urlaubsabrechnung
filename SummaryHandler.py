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
											
class SummaryHandler(BaseRequestHandler):
	def	get(self):
		(project, right)=self.getandcheckproject(1)
		# build dictionary which translates the each group into a percentage how each person is accounted for		
		groups = dict()
		debits = dict()
		credits = dict()
		names = dict()
		accounts = []
		for account in project.person_set:
			# reset account
			credits[account.key()]=0
			debits[account.key()]=0
			names[account.key()]=account.name
			if isinstance(account, Person):				
				accounts=accounts+[account.key()]	# create a list of all real person accounts
			elif isinstance(account, Group):
				parts=dict()
				sum=0
				for member in account.member_set:
					parts[member.person.key()]=member.weight
					sum=sum+member.weight
				# normalize group weights
				for key in parts.iterkeys():
					parts[key]=parts[key]/sum
				# save reference to normalized list
				groups[account.key()]=parts
		#  create debits and credits
		for transaction in project.transaction_set:
			if transaction.currency: 
				d=transaction.currency.divisor 
			else: 
				d=float(1)
			c = transaction.ammount/d
			if c>0:
				credits[transaction.source.key()]=credits[transaction.source.key()]+c
				debits[transaction.dest.key()]=debits[transaction.dest.key()]+c
			else:
				credits[transaction.dest.key()]=credits[transaction.dest.key()]-c
				debits[transaction.source.key()]=debits[transaction.source.key()]-c
		# distribute debits and credits of groups among the members
		credit_results=dict()
		debit_results=dict()
		for group in groups:
			credit_result=dict()
			debit_result=dict()
			weights = groups[group]
			for account in weights.iterkeys():
				credit_result[account]=credits[group]*weights[account]
				debit_result[account]=debits[group]*weights[account]
			credit_results[group]=credit_result
			debit_results[group]=debit_result
		# reset row sums
		debit_rsums=dict()
		credit_rsums=dict()
		# output all as table
		res = StringIO.StringIO()
		res.write('<table>')
		# header line 1
		res.write('<tr><td>&nbsp;</td>')
		for account in accounts:
			res.write('<td colspan="2"><center>%(name)s</center></td>' % {'name':names[account]})
		res.write('<td colspan="2"><center>column sum</center></td></tr>')
		# header line 2
		res.write('<tr><td></td>')
		for account in accounts:
			res.write('<td>Debit</td><td>Credit</td>')
		res.write('<td>Debit</td><td>Credit</td></tr>')		
		# special cash line
		res.write('<tr><td>Cash</td>')
		credit_csum=0
		debit_csum=0
		for account in accounts:
			res.write('<td>%(debit).2f</td><td>%(credit).2f</td>' % {'debit':debits.get(account,0), 'credit':credits.get(account,0)})
			credit_csum=credit_csum+credits.get(account,0)
			debit_csum=debit_csum+debits.get(account,0)
			credit_rsums[account]=credit_rsums.get(account,0)+credits.get(account,0)
			debit_rsums[account]=debit_rsums.get(account,0)+debits.get(account,0)
		res.write('<td>%(debit).2f</td><td>%(credit).2f</td>' % {'debit':debit_csum, 'credit':credit_csum})
		res.write('</tr>')
		credit_rsums[0]=credit_rsums.get(0,0)+credit_csum
		debit_rsums[0]=debit_rsums.get(0,0)+debit_csum
		# all other groups
		for group in groups:
			# credit row
			res.write('<tr>')
			res.write('<td>%(name)s</td>' % {'name':names[group]})
			credit_result=credit_results[group]
			debit_result=debit_results[group]
			for account in accounts:
				credit_rsums[account]=credit_rsums.get(account,0)+credit_result.get(account,0)
				debit_rsums[account]=debit_rsums.get(account,0)+debit_result.get(account,0)
				res.write('<td>%(debit).2f</td><td>%(credit).2f</td>' % {'debit':debit_result.get(account,0), 'credit':credit_result.get(account,0)})
			res.write('<td>%(debit).2f</td><td>%(credit).2f</td>' % {'debit':debits[group], 'credit':credits[group]})
			res.write('</tr>')
			credit_rsums[0]=credit_rsums.get(0,0)+credits[group]
			debit_rsums[0]=debit_rsums.get(0,0)+debits[group]
		# totals row
		res.write('<tr><td>row sum</td>')
		for account in accounts:
			res.write('<td>%(debit).2f</td><td>%(credit).2f</td>' % {'debit':debit_rsums.get(account,0), 'credit':credit_rsums.get(account,0)})
		res.write('<td>%(debit).2f</td><td>%(credit).2f</td>' % {'debit':debit_rsums.get(0,0), 'credit':credit_rsums.get(0,0)})
		res.write('</tr>')
		# final results row
		res.write('<tr><td>result</td>')
		for account in accounts:
			s=credit_rsums.get(account,0)-debit_rsums.get(account,0)
			if s>0:
				res.write('<td/><td>%(result).2f</td>' % {'result':s})
			else:
				res.write('<td><font color="red">%(result).2f</font></td><td/>' % {'result':(-s)})
		s=credit_rsums.get(0,0)-debit_rsums.get(0,0)
		if s>0:
			res.write('<td/><td>%(result).2f</td>' % {'result':s})
		else:
			res.write('<td>%(result).2f</td><td/>' % {'result':(-s)})
		res.write('</tr></table>')		
		# generate output
		self.generate('summary', {
			'project': project,
			'project_key': project.key(),
			'txt': res.getvalue()
		})
