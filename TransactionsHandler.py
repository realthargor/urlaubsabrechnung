#!/usr/bin/env python

from models import Transaction, Account, Currency
from BaseRequestHandler import BaseRequestHandler

from google.appengine.ext.webapp.util import login_required
from datetime import datetime
						
class TransactionsHandler(BaseRequestHandler):
	def sendTransactionList(self):
		self.generate('transaction_data',
		{
			'transactions': sorted(self.project.transaction_set, cmp=lambda x, y: cmp(x.date, y.date))
		})

	# this handler handles all transaction transfer requests
	def	post(self):
		self.updateproject()
		action = self.request.get('action', 'list')
		if action == 'list':
			self.sendTransactionList()		
		elif action == 'update':
			# add a new or update a transaction
			tkey = self.request.get('transaction', 'None')
			if tkey == 'None':
				transaction = Transaction()
				transaction.project = self.project
			else:
				transaction = Transaction.get(tkey)
				if transaction.project.key() != self.project.key():
					raise Exception("Project/Transaction mismatch")
			# update / set fields
			transaction.date = datetime.strptime(self.request.get('date', transaction.date.isoformat()), "%Y-%m-%d")
			transaction.source = Account.get(self.request.get('source', transaction.source and transaction.source.key()))
			transaction.dest = Account.get(self.request.get('dest', transaction.dest and transaction.dest.key()))
			transaction.ammount = float(self.request.get('ammount', str(transaction.ammount)).replace(',', '.'))
			transaction.check = self.request.get('check', 'False') == 'True'
			transaction.text = self.request.get('text', transaction.text)
			# a None currency means we use the base currency!
			c = self.request.get('currency', transaction.currency and transaction.currency.key())
			transaction.currency = Currency.get(c) if c != "None" else None
			# exchange source and dest, if the amount is negative
			if transaction.ammount < 0:
				tmp_src = transaction.source
				transaction.source = transaction.dest
				transaction.dest = tmp_src
				transaction.ammount = -transaction.ammount	
			# put back into data store
			transaction.put()
			# retransmit all transactions
			self.sendTransactionList()
		elif action == 'delete':
			# add a new or update a transaction
			transaction = Transaction.get(self.request.get('transaction', 'None'))
			if transaction.project.key() != self.project.key():
				raise Exception("Project/Transaction mismatch")
			transaction.delete()
			# retransmit all transactions
			self.sendTransactionList()			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
	
	# This handler shows the main transactions page
	@login_required
	def	get(self):
		self.updateproject()
		self.generate('transactions')
		
