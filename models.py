#!/usr/bin/env python
# ******************************************************************************
# ** DATA MODELS ***************************************************************
# ******************************************************************************
import os
import cgi
import datetime
import StringIO

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template 
from google.appengine.ext.db import polymodel
from google.appengine.ext.db import BadKeyError
from google.appengine.ext.webapp.util import login_required

class Project(db.Model):
	name = db.StringProperty()
	currency = db.StringProperty()  
	
	""" returns a list of endpoint accounts """
	def Endpoints(self):
		return filter(lambda a: a.IsEndpoint(), self.person_set)
	
	""" Helper to format a single value """
	def formatTableValue(self, value):
		if value<0:
			return '<td style="color: red; text-align:right;">%(v).2f%(unit)s</td>' % {'v':-value, 'unit': self.currency }
		elif value>0:
			return '<td style="color: black; text-align:right;">%(v).2f%(unit)s</td>' % {'v':value, 'unit': self.currency}
		else:
			return "<td/>"
			
	""" Group definition list """
	def GroupDefList(self):
		res = StringIO.StringIO()
		res.write('<ul>')
		for account in filter(lambda a: not a.IsEndpoint(), self.person_set):
			res.write('<li>')
			res.write(account.name)
			res.write(' (')
			parts = account.enquire(100, balance=dict())
			for partKey in parts:
				member = Account.get(partKey)
				res.write('%(part).2f%% %(name)s, ' % {
					'name': member.name,
					'part': parts[partKey]
				})
			res.write(')</li>')
		res.write('</ul>')
		return res.getvalue()			

	""" Currency defintion list """
	def CurrencyDefList(self):
		res = StringIO.StringIO()
		res.write('<ul>')
		for currency in self.currency_set:
			if currency.divisor>0:				
				res.write('<li>1 %(base)s = %(divisor)f %(name)s</li>' % {
					'name': currency.name,
					'divisor': currency.divisor,
					'base': self.currency
				})
			elif currency.divisor<0:
				res.write('<li>1 %(name)s = %(factor)f %(base)</li>' % {
					'name': currency.name,
					'factor': 1/currency.divisor,
					'base': self.currency
				})
		res.write('</ul>')
		return res.getvalue()
		
	""" returns string with a a html table of all transactions """
	def TransactionTable(self):
		# TRANSACTIONS
		res = StringIO.StringIO()
		eps = self.Endpoints()
		res.write("""
		<table border="1" cellspacing="1" cellpadding="0">
			<thead>
				<tr>
					<th colspan="6"/>
					<th colspan="%(endpoints)d">Belastung</th>
				</tr>
				<tr>
					<th>Datum</th>
					<th>Was</th>
					<th>Wert</th>
					<th>Von</th>
					<th>An</th>
					<th>Letzte Aenderung</th>""" % { 
						'baseCurrency': self.currency,
						'endpoints': len(eps)
					} )				
		for ep in eps: 
			res.write('<th>%(name)s</th>' % { 'name': ep.name, 'baseCurrency': self.currency } )
		res.write('</tr></thead><tbody>')				
		sums = dict()
		for transaction in self.transaction_set:
			res.write("""
					<tr>
						<td>%(date)s</td>
						<td>%(text)s</td>
						<td >%(amount).2f%(currency)s</td>
						<td>%(source)s</td>
						<td>%(dest)s</td>
						<td>%(lastmodified)s by %(modifiedby)s</td>""" % { 
							'date': transaction.date.strftime("%d.%m.%Y"),
							'source': transaction.source.name,
							'dest': transaction.dest.name,
							'amount': transaction.ammount,
							'currency': transaction.CurrencyName(),
							'amountBase': transaction.AmountBase(),
							'text': transaction.text,
							'lastmodified': transaction.lastmod,
							'modifiedby': transaction.user
						})
			affected = transaction.UpdateSums(balance=dict())
			transaction.UpdateSums(balance=sums)
			for ep in eps: 
				res.write(self.formatTableValue(affected.get(ep.key(),0)))
			res.write('</tr></thead><tbody>')
		res.write('</tbody><tfoot><td colspan="6">Endergebnis (rot=Soll, schwarz=Haben)</td>')
		for ep in eps: 
			res.write(self.formatTableValue(sums.get(ep.key(), 0)))
		res.write('</tfoot></table>')		
		return res.getvalue()
  
class Account(polymodel.PolyModel):
	name = db.StringProperty(required=True)
	def IsEndpoint(self):
		return isinstance(self, Person) or sum([abs(member.weight) for member in self.member_set])==0	
	
	""" return the sum of weights for the given group """
	def SumOfMemberWeigths(self):
		return sum([abs(member.weight) for member in self.member_set]) if isinstance(self, Group) else 0

	""" Calculates which final accounts are affected by an enquire to the given account """
	def enquire(self, amount, balance=dict(), sign=1):
		# make sure the amount is rounded
		amount = round(amount, 2)
		# calculate the sum of weights
		sweight = self.SumOfMemberWeigths()
		# when the weight sum is zero, that means, there are no valid members, thus we map that to the account
		if sweight==0:
			balance[self.key()]=balance.get(self.key(),0)+sign*amount;
			return balance
		# now we create a dictionary
		ramount = amount		# remaing amount
		rweight = sweight		# remaing sum of weights
		# walk through the sorted list, the last member (the one with the largest weight) gets the remaining sum
		for member in sorted(self.member_set, cmp=lambda x,y: cmp(x.weight, y.weight)):
			rweight-=abs(member.weight)
			val = round(amount*abs(member.weight)/sweight, 2) if rweight>0 else ramount
			ramount-=val
			balance[member.person.key()]=balance.get(member.person.key(),0)+sign*val;
		# return dictionary again
		return balance

class Person(Account):
  project = db.ReferenceProperty(Project)
  
class Group(Account):
  project = db.ReferenceProperty(Project)
  
class Member(db.Model):
  group = db.ReferenceProperty(Group)
  person = db.ReferenceProperty(Person)
  weight = db.FloatProperty()	
    
class Currency(db.Model):
  project = db.ReferenceProperty(Project)
  name = db.StringProperty()
  divisor = db.FloatProperty()
   
class Transaction(db.Model):
	project = db.ReferenceProperty(Project)
	source = db.ReferenceProperty(Account, collection_name="accountmodel_reference_source_set")
	dest = db.ReferenceProperty(Account, collection_name="accountmodel_reference_dest_set")
	ammount = db.FloatProperty()
	currency = db.ReferenceProperty(Currency)
	text = db.StringProperty()  
	date = db.DateTimeProperty(auto_now_add=True)
	user = db.UserProperty(auto_current_user=True)
	lastmod = db.TimeProperty(auto_now=True)
	
	""" returns the amount of the transaction using in the project currency """
	def AmountBase(self):
		return self.ammount/self.currency.divisor if self.currency else self.ammount
	
	""" returns the currency text """
	def CurrencyName(self):
		return self.currency.name if self.currency else self.project.currency
			
	def UpdateSums(self, balance=dict()):
		self.dest.enquire(amount=self.AmountBase(),balance=balance, sign=-1)
		self.source.enquire(amount=self.AmountBase(),balance=balance, sign=+1)
		return balance

class ProjectRights(db.Model):
  project = db.ReferenceProperty(Project, required=True)
  user = db.UserProperty(required=True)
  right = db.IntegerProperty()
  
"""
	Invitation represents a not yet turned in access key to a project with the given rights
	The invited person receives an email together with the key of the invitation and a random
	access code for safety.
	Once the user clicks the link containing both codes, a ProjectRights instance is created and the original invitation
	is deleted.
"""
class Invitation(db.Model):
  project = db.ReferenceProperty(Project, required=True)
  invited_by = db.UserProperty(auto_current_user=True)
  user = db.UserProperty(required=True)
  right = db.IntegerProperty(required=True)
  code = db.IntegerProperty(required=True)
  created = db.TimeProperty(auto_now_add=True)  
