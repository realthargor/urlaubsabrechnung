#!/usr/bin/env python
# ******************************************************************************
# ** DATA MODELS ***************************************************************
# ******************************************************************************

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.db import polymodel
import Security

class Project(db.Model):
	name = db.StringProperty() # default name for all ProjectAccess
	currency = db.StringProperty()
	state = db.IntegerProperty(default=0) # 0..open, 1..closing, 2..closed

	""" returns a list of endpoint accounts """
	def Endpoints(self):
		return filter(lambda a: a.IsEndpoint(), self.person_set)

	""" checks weather the given name is a valid new name for a a new account or a given existing account """
	def CheckNewAccountName(self, name, account=None):
		if len(name) < 1:
			raise Exception("account name must be at least on character long")
		for a in self.person_set:
			if a.name == name and (account == None or a.key() != account.key()):
				raise Exception("duplicate name")

	""" defines accounts and transactions members for the project summary report """
	def CalculateResult(self):
		# GROUPS
		self.groups = dict()
		for g in filter(lambda a: not a.IsEndpoint(), self.person_set):
			g.sum = 0
			g.credit = 0
			g.debit = 0
			for member in g.member_set:
				g.sum+=abs(member.weight)
			g.members = []
			for member in g.member_set:
				person = member.person
				person.weight=abs(member.weight)
				person.part=100*person.weight/g.sum
				g.members.append(person)
			self.groups[str(g.key())] = g;
		# PERSONS
		self.persons = dict()
		for person in sorted(self.Endpoints(), cmp=lambda x, y: cmp(x.name, y.name)):
			person.sum=0
			person.credit=0
			person.debit=0
			self.persons[str(person.key())]=person
		# TRANSACTIONS
		self.transactions = [];
		for transaction in sorted(self.transaction_set, cmp=lambda x, y: cmp(x.date, y.date)):
			# add up credit sum, for persons/groups
			if transaction.source.IsEndpoint():
				self.persons[str(transaction.source.key())].credit+=transaction.AmountBase()
			else:
				self.groups[str(transaction.source.key())].credit+=transaction.AmountBase()
			# add up debit sum, for persons/groups
			if transaction.dest.IsEndpoint():
				self.persons[str(transaction.dest.key())].debit+=transaction.AmountBase()
			else:
				self.groups[str(transaction.dest.key())].debit+=transaction.AmountBase()
			# update list of affected persons
			affected = transaction.UpdateSums(balance=dict())
			transaction.affected = [{
									'value':affected.get(endpoint.key(), 0),
									'negative':affected.get(endpoint.key(), 0)<0,
									'positive':affected.get(endpoint.key(), 0)>0,
									} for endpoint in self.persons.values()];
			for (key, value) in affected.iteritems():
				self.persons[str(key)].sum+=value
			self.transactions.append(transaction)
		# GROUPS
		for group in self.groups.values():
			group.credit_minus_debit = group.credit - group.debit
		# PERSONS
		for person in self.persons.values():
			person.sum_negative = person.sum<=-0.005
			person.sum_positive = person.sum>=+0.005
			person.group_part = person.sum - (person.credit - person.debit)

			
"""
	Base class for any project access, the ancestor class should override the _str_(self) method to get a qualified name
"""
class ProjectAccess(db.Model):
	project = db.ReferenceProperty(Project, required=True)
	right = db.IntegerProperty()
	local_name = db.StringProperty(default="")

	def RightView(self): return self.right >= Security.Right_View
	def RightEdit(self): return self.right >= Security.Right_Edit;
	def RightManage(self): return self.right >= Security.Right_Manage;
	def RightOwner(self): return self.right >= Security.Right_Owner;

	"""
		Creates a new ProjectAccess instance depending on the given token, when the token is empty None is returned
	"""
	@staticmethod
	def GetFromToken(token_key):
		if token_key=="": return None
		token_data = token_key.rsplit('_', 1)
		if token_data[0]=="admin" and len(token_data)==2:
			token = ProjectAccessAdmin.Create(token_data[1])
		else:
			token =  ProjectAccessTicket.get(token_data[0]) if len(token_data) == 2 else ProjectAccessAuthenticated.get(token_key)
		token.CheckPermission(code=token_data[-1], requested_permission=Security.Right_Minimum)
		return token
		
	"""
		Returns the access token for a given project and user/ticket
	"""
	def Token(self):
		return str(self.key())
		
	"""
		Performs a permisson check for the requested permission, if the permission is not granted an exception is raised
	"""
	def CheckPermission(self, code=None, requested_permission=Security.Right_None):
		if self.right < requested_permission:
			raise Exception("Permission denied!")

	"""
		Returns a list of ProjectAccess objects for the current user or None, if not applicable
	"""
	@staticmethod
	def ListUserProjects():
		u = users.get_current_user()
		return ProjectAccessAuthenticated.gql("WHERE user=:user AND right>=:minright", user=u, minright=Security.Right_Minimum) if u!=None else None

	@staticmethod
	def ListProjectsAsAdmin():
		# super user sees all projects
		return [ProjectAccessAdmin.Create(key=str(p.key())) for p in Project.all()] if users.is_current_user_admin() else None

	"""
		Returns the Projects Display Name defined by the current ProjectAccess
	"""
	def DisplayName(self):
		return self.local_name + " (" + self.project.name + ")" if self.local_name and self.local_name != '' else self.project.name

	"""
		should return a meaningfull name identifying the user, e.g. the username or a ticket name, whatever
	"""
	def UserName(self):
		return users.get_current_user().nickname()
		
	def HasProjectList(self):
		return False

"""
	Authenticated project access by a logged on super user
"""
class ProjectAccessAdmin(ProjectAccess):
	@staticmethod
	def Create(key):
		return ProjectAccessAdmin(project=Project.get(key), right=Security.Right_Admin, local_name="AdminMode")
		
	def CheckPermission(self, code=None, requested_permission=Security.Right_None):
		if users.is_current_user_admin():
			return
		raise Exception("Permission denied!")

	def Token(self):
		return "admin_"+str(self.project.key())

	def UserName(self):
		return users.get_current_user().nickname() + " (Admin)"
	
	def HasProjectList(self):
		return True

"""
	Authenticated project access by a logged on user
"""
class ProjectAccessAuthenticated(ProjectAccess):
	user = db.UserProperty(required=True)
	def CheckPermission(self, code=None, requested_permission=Security.Right_None):
		# check the ticket code and additionally check if the ticket expired
		if users.get_current_user() != self.user:
			raise Exception("Permission denied!")
		return ProjectAccess.CheckPermission(self, code=code, requested_permission=requested_permission)

	def UserName(self):
		return self.user.nickname()

	def HasProjectList(self):
		return True

"""
	A Ticket is anonymous way to access a project for a given time
"""
class ProjectAccessTicket(ProjectAccess):
	name = db.StringProperty(required=True)
	code = db.IntegerProperty(required=True)
	expires = db.DateTimeProperty()
	
	def CheckPermission(self, code=None, requested_permission=Security.Right_None):
		# check the ticket code and additionally check if the ticket expired
		if datetime.today() > self.expires or code != self.code:
			raise Exception("Permission denied!")
		return ProjectAccess.CheckPermission(self, code=code, requested_permission=requested_permission)
	
	def UserName(self):
		return self.name
	"""
		Returns the access token for a given project and user/ticket
	"""
	def Token(self):
		return str(self.key())+"_"+str(self.code)

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
	changedby = db.ReferenceProperty(ProjectAccess)
	check = db.BooleanProperty(default=False)
	lastmod = db.DateTimeProperty(auto_now=True)

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

"""
	Invitation represents a not yet turned in access key to a project with the given rights
	The invited person receives an email together with the key of the invitation and a random
	access code for safety.
	Once the user clicks the link containing both codes, a ProjectAccessAuthenticated instance is created and the original invitation
	is deleted.
"""
class Invitation(db.Model):
	project = db.ReferenceProperty(Project, required=True)
	invited_by = db.ReferenceProperty(ProjectAccess, required=True)
	user = db.UserProperty(required=True)
	right = db.IntegerProperty(required=True)
	code = db.IntegerProperty(required=True)
	created = db.DateTimeProperty(auto_now_add=True)
