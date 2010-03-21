#!/usr/bin/env python
# ******************************************************************************
# ** DATA MODELS ***************************************************************
# ******************************************************************************
import StringIO

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.db import polymodel
from google.appengine.ext.db import BadKeyError

class Project(db.Model):
	name = db.StringProperty()
	currency = db.StringProperty()
	
	""" constructs a new project from a given key (the rights are added using the given user rights) """
	@staticmethod
	def get(key):
		project = db.Model.get(key)
		if not isinstance(project, Project):
			raise BadKeyError("Not a project key!")
		project.rights = 0x7FFFFFFF if users.is_current_user_admin() else ProjectRights.gql("WHERE user=:user and project=:project", user=users.get_current_user(), project=project).get().right
		return project			
	
	""" returns all list of all projects the user actually has rights for """
	@staticmethod
	def all():
		projects = ()
		for right in ProjectRights.gql("WHERE user=:user AND right>0", user=users.get_current_user()):
			right.project.rights = right.right			
			projects.append(right.project)
		return projects				
		
	def RightReport(self):
		return self.rights & 1
		
	def RightTransaction(self):
		return self.rights & (2 | 4 | 8)
		
	def RightReportView(self):
		return self.rights & 1
	
	def RightTransactionNew(self):
		return self.rights & 2

	def RightTransactionUpdate(self):
		return self.rights & 4

	def RightTransactionDelete(self):
		return self.rights & 8
		
	def RightAccountAdd(self):
		return self.rights & 16

	def RightAccountRemove(self):
		return self.rights & 32

	def RightMembershipUpdate(self):
		return self.rights & 64

	def RightCurrencyAdd(self):
		return self.rights & 128
		
	def RightCurrencyUpdate(self):
		return self.rights & 256

	def RightCurrencyDelete(self):
		return self.rights & 512

	def RightAccessAdd(self):
		return self.rights & 1024

	def RightAccessDelete(self):
		return self.rights & 2048

	def RightAccessUpdate(self):
		return self.rights & 4096
		
	""" returns a list of endpoint accounts """
	def Endpoints(self):
		return filter(lambda a: a.IsEndpoint(), self.person_set)
		
	""" checks wether the given name is a valid new name for a a new account or a given existing account """
	def CheckNewAccountName(self, name, account=None):
		if len(name) < 1:
			raise Exception("account name must be at least on character long")
		for a in self.person_set:
			if a.name == name and (account == None or a.key() != account.key()):
				raise Exception("duplicate name")
				
	""" Helper to format a single value """
	def formatTableValue(self, value):
		if value < 0:
			return '<td style="color: red; text-align:right;">%(v).2f%(unit)s</td>' % {'v':-value, 'unit': self.currency }
		elif value > 0:
			return '<td style="color: black; text-align:right;">%(v).2f%(unit)s</td>' % {'v':value, 'unit': self.currency}
		else:
			return "<td/>"
			
	""" Group definition list """
	def GroupDefList(self):
		res = StringIO.StringIO()
		res.write('<ul>')
		for account in filter(lambda a: not a.IsEndpoint(), self.person_set):
			parts = account.enquire(100, balance=dict())
			res.write('<li>%(name)s &rArr; %(members)s</li>' % {
				'name':account.name,
				'members': ', '.join(
					[
						'%(part).2f%% %(name)s' % {'name': Account.get(partKey).name, 'part':parts[partKey] } 
					for partKey in parts]
					)
			})
		res.write('</ul>')
		return res.getvalue()			

	""" Currency defintion list """
	def CurrencyDefList(self):
		res = StringIO.StringIO()
		res.write('<ul>')
		for currency in self.currency_set:			
			if currency.divisor == 1 :
				res.write('<li>%(divisor)f %(name)s = %(factor)f %(base)s</li>' % {
					'name': currency.name, 	
					'factor': currency.factor,
					'divisor': currency.divisor,
					'base': self.currency
				})				
			else:
				res.write('<li>%(factor)f %(base)s = %(divisor)f %(name)s</li>' % {
					'name': currency.name, 	
					'factor': currency.factor,
					'divisor': currency.divisor,
					'base': self.currency
				})
		res.write('</ul>')
		return res.getvalue()
		
	""" returns string with a a html table of all transactions """
	def ResultData(self):
		# TRANSACTIONS
		res = dict()
		endpoints = self.Endpoints()
		res['endpoints'] = endpoints
		sums = dict()
		tr = [];
		for transaction in sorted(self.transaction_set, cmp=lambda x, y: cmp(x.date, y.date)):
			affected = transaction.UpdateSums(balance=dict())
			transaction.affected = [affected.get(endpoint.key(), 0) for endpoint in endpoints]
			for (key, value) in affected.iteritems():
				sums[key] = sums.get(key, 0) + value
			tr.append(transaction)
		res['transactions'] = tr
		res['sums'] = [ round(sum, 2) for sum in sums.itervalues() ]
		return res


class Account(polymodel.PolyModel):
	name = db.StringProperty(required=True)
	def IsEndpoint(self):
		return isinstance(self, Person) or sum([abs(member.weight) for member in self.member_set]) == 0	
		
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
		if sweight == 0:
			balance[self.key()] = balance.get(self.key(), 0) + sign * amount;
			return balance
		# now we create a dictionary
		ramount = amount		# remaing amount
		rweight = sweight		# remaing sum of weights
		# walk through the sorted list, the last member (the one with the largest weight) gets the remaining sum
		for member in sorted(self.member_set, cmp=lambda x, y: cmp(x.weight, y.weight)):
			rweight -= abs(member.weight)
			val = round(amount * abs(member.weight) / sweight, 2) if rweight > 0 else ramount
			ramount -= val
			balance[member.person.key()] = balance.get(member.person.key(), 0) + sign * val
		# return dictionary again
		return balance
		
	""" returns the number of transactions affected by deleting this Account """
	def ByDeleteAffectedTransactions(self):
		return len(self.accountmodel_reference_source_set) + len(self.accountmodel_reference_dest_set)
		
	""" overwrites polymodel.PolyModel.delete() and also deletes all references """
	def delete(self):
		# delete transactions asociated with this person as source
		for t in self.accountmodel_reference_source_set:
			t.delete()
		# delete transactions asociated with this person as dest
		for t in self.accountmodel_reference_dest_set: 
			t.delete()		
		# call base method (which actually deletes this instance from the data store)
		polymodel.PolyModel.delete(self)

class Person(Account):
	project = db.ReferenceProperty(Project)
	""" overwrites polymodel.PolyModel.delete() and also deletes all references """
	def delete(self):
		# delete all membership definitions
		for membership in self.member_set:
			membership.delete()
		# call base method (which actually deletes this instance from the data store)
		Account.delete(self)

class Group(Account):
	project = db.ReferenceProperty(Project)
	
	""" overwrites polymodel.PolyModel.delete() and also deletes all references """
	def delete(self):
		# delete all membership definitions
		for membership in self.member_set:
			membership.delete()
		# call base method (which actually deletes this instance from the data store)
		Account.delete(self)
	

class Member(db.Model):
	group = db.ReferenceProperty(Group)
	person = db.ReferenceProperty(Person)
	weight = db.FloatProperty()	

class Currency(db.Model):
	project = db.ReferenceProperty(Project)
	name = db.StringProperty()
	factor = db.FloatProperty(default=1.0)
	divisor = db.FloatProperty(default=1.0)

class Transaction(db.Model):
	project = db.ReferenceProperty(Project)
	source = db.ReferenceProperty(Account, collection_name="accountmodel_reference_source_set")
	dest = db.ReferenceProperty(Account, collection_name="accountmodel_reference_dest_set")
	ammount = db.FloatProperty()
	currency = db.ReferenceProperty(Currency)
	text = db.StringProperty()  
	date = db.DateTimeProperty(auto_now_add=True)
	user = db.UserProperty(auto_current_user=True)
	check = db.BooleanProperty(default=False)
	lastmod = db.TimeProperty(auto_now=True)
	
	""" returns the amount of the transaction using in the project currency """
	def AmountBase(self):
		return self.ammount * self.currency.factor / self.currency.divisor if self.currency else self.ammount
	
	""" returns the currency text """
	def CurrencyName(self):
		return self.currency.name if self.currency else self.project.currency
			
	def UpdateSums(self, balance=dict()):
		self.dest.enquire(amount=self.AmountBase(), balance=balance, sign= -1)
		self.source.enquire(amount=self.AmountBase(), balance=balance, sign= +1)
		return balance

class ProjectRights(db.Model):
	project = db.ReferenceProperty(Project, required=True) #@IndentOk
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
