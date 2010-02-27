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
						
class TransactionsHandler(BaseRequestHandler):
	def sendTransactionList(self, project, right):
		self.generate('transaction_data', {
			'transactions':  [
				{
					't':t,
					'key':t.key(),
					'source_key': t.source.key(),
					'dest_key': t.dest.key(),
					'currency_key': t.currency and t.currency.key(),
				} for t in project.transaction_set],
			'project': project,
		})

	# this handler handles all transaction transfer requests
	def	post(self):
		(project, right)=self.getandcheckproject(1)
		action = self.request.get('action','list')
		if action=='list':
			self.sendTransactionList(project, right)		
		elif action=='update':
			# add a new or update a transaction
			tkey=self.request.get('transaction','None')
			if tkey=='None':
				transaction = Transaction()
				transaction.project = project
			else:
				transaction = Transaction.get(tkey)
				if transaction.project.key()!=project.key():
					raise Exception("Project/Transaction mismatch")
			# update / set fields
			transaction.date = datetime.strptime(self.request.get('date', transaction.date.isoformat()), "%Y-%m-%d")
			transaction.source = Account.get(self.request.get('source', transaction.source and transaction.source.key()))
			transaction.dest = Account.get(self.request.get('dest', transaction.dest and transaction.dest.key()))
			transaction.ammount = float(self.request.get('ammount', str(transaction.ammount)).replace(',','.'))
			# a None currency means we use the base currency!
			c = self.request.get('currency', transaction.currency and transaction.currency.key())
			if c=="None":
				transaction.currency = None
			else:
				transaction.currency = Currency.get(c)
			transaction.text = self.request.get('text', transaction.text)
			# exchange source and dest, if the ammount is negative
			if transaction.ammount<0:
				tmp_src = transaction.source
				transaction.source = transaction.dest
				transaction.dest = tmp_src
				transaction.ammount=-transaction.ammount	
			# put back into datastore
			transaction.put()
			# retransmit all transactions
			self.sendTransactionList(project, right)
		elif action=='delete':
			# add a new or update a transaction
			transaction = Transaction.get(self.request.get('transaction','None'))
			if transaction.project.key()!=project.key():
				raise Exception("Project/Transaction mismatch")
			transaction.delete()
			# retransmit all transactions
			self.sendTransactionList(project, right)			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
	
	# This handler shows the main transactions page
	def	get(self):
		(project, right)=self.getandcheckproject(1)
		self.generate('transactions', {
			'project': project,
			'project_key': project.key(),
		})
