#!/usr/bin/env python
import os
import cgi
import datetime
import wsgiref.handlers
import StringIO
import random

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

# Set to true if we want to have our webapp print stack traces, etc
_DEBUG = True

# ******************************************************************************
# ** DATA MODELS ***************************************************************
# ******************************************************************************
class Project(db.Model):
  name = db.StringProperty()
  currency = db.StringProperty()
  
class Account(polymodel.PolyModel):
  name = db.StringProperty(required=True)

class Person(Account):
  project = db.ReferenceProperty(Project)
  pass
  
class Group(Account):
  project = db.ReferenceProperty(Project)
  pass
  
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
 
# ******************************************************************************
# ** Base class for all handlers ***********************************************
# ******************************************************************************
class BaseRequestHandler(webapp.RequestHandler):
	"""Supplies a common template generation function.
	When you call generate(), we augment the template variables supplied with
	the current user in the 'user' variable and the current webapp request
	in the 'request' variable.
	"""
	def generate(self, template_name, template_values={}):
		values = {
		  'request': self.request,
		  'user': users.GetCurrentUser(),
		  'login_url': users.CreateLoginURL(self.request.uri),
		  'logout_url': users.CreateLogoutURL(self.request.uri),
		  'application_name': 'Urlaubsabrechnung',
		}
		values.update(template_values)
		directory = os.path.dirname(__file__)
		path = os.path.join(directory, os.path.join('templates', template_name + '_en.html'))
		self.response.out.write(template.render(path, values, debug=_DEBUG))
		
	"""(OBSOLETE) use @login instead! Checks, if a user is logged on, redirects to login page """
	def checklogin(self):
		if not users.GetCurrentUser():
			self.generate("login", { })
			return True
		return False
				
	def _handle_exception(self, exception, debug_mode):
		self.response.clear()
		self.response.set_status(400)
		self.response.out.write('<p>%(message)s</p>' % {'message':str(exception)})
	
	# checks, if the user has at least the required rights
	# to the given project
	# throws an exception, if the rights are not sufficent
	# returns a tuple with actual project and the  rights otherwise	
	def getandcheckproject(self, required_rights):
		project = Project.get(self.request.get('project',''))
		if (not project):
			raise Exception("Unknown project!")
		# check rights of current user for this project, and deny access if not permitable
		rights = ProjectRights.gql("WHERE user=:user and project=:project", user=users.get_current_user(), project=project).get()
		if (not rights) or (rights.right<required_rights):
			raise Exception("Access denied!")
		return (project, rights.right)
						
# ******************************************************************************
# ** ACTUAL HANDLERS ***********************************************************
# ******************************************************************************
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

# ******************************************************************************
# ** ACTUAL HANDLERS ***********************************************************
# ******************************************************************************
class AccountsHandler(BaseRequestHandler):
	def listGroups(self, project, type, default):
		# list remaining groups
		for a in project.person_set:
			if isinstance(a, type):
				if default==None or default.key()==a.key():
					self.response.out.write('<option selected value="%(value)s">%(name)s</option>' % {'name':a.name, 'value':a.key()})
					default=a	# this prevents from getting default again
				else:
					self.response.out.write('<option value="%(value)s">%(name)s</option>' % {'name':a.name, 'value':a.key()})
		
	def	post(self):
		(project, right)=self.getandcheckproject(1)
		action = self.request.get('action','list')		 
		if action=='list':
			# select the class type we want to list
			type = self.request.get('type', 'all')
			if type=='person': 
				target_class=Person 
			elif type=='group':
				target_class=Group
			else:
				target_class=object
			# create a list of options against all accounts
			self.listGroups(project, target_class, None)
		
		elif action=='member_remove':
			# remove memberships
			group = Group.get(self.request.get('group'))
			for member_key in json.loads(self.request.get('member_list')):
				m = Member.get(member_key)
				if m.group.key()==group.key():
					m.delete()
			# list members of a group
			for member in Group.get(self.request.get('group')).member_set:
				self.response.out.write('<option value="%(value)s">%(name)s: %(weight)f</option>' % {'name':member.person.name, 'value':member.key(), 'weight': member.weight })
		
		elif action=='member_add':
			# add or update memberships
			group = Group.get(self.request.get('group'))
			member_weight = float(self.request.get('member_weight', '1'))
			update_account_list = json.loads(self.request.get('account_key_list'))
			# first update existing member weights
			for m in group.member_set:
				k=str(m.person.key())
				if k in update_account_list:
					m.weight = member_weight
					update_account_list.remove(k)
					m.put()
			# add new memberships for all remaining items
			for a in update_account_list:
				Member(project=project, group=group, weight=member_weight, person=Person.get(a)).put()
			# delete all members with weight 0
			for member in Group.get(self.request.get('group')).member_set:
				if member.weight == 0:
					member.delete()
			# list members of a group
			for member in Group.get(self.request.get('group')).member_set:
				self.response.out.write('<option value="%(value)s">%(name)s: %(weight)f</option>' % {'name':member.person.name, 'value':member.key(), 'weight': member.weight })
				
		elif action=='group_add':
			# add a new group
			group = Group(name=self.request.get('name'), project=project)
			group.put()
			# list new remaining groups
			self.listGroups(project, Group, group)
			
		elif action=='person_add':
			# add a new person
			person = Person(name=self.request.get('name'), project=project)
			person.put()
			# list the persons
			self.listGroups(project, Person, person)
			
		elif action=='person_remove':
			# remove a group
			for person_key in json.loads(self.request.get('person_list')):
				person = Person.get(person_key)
				# delete transactions asociated with this person as source
				for t in person.accountmodel_reference_source_set:
					t.delete()
				# delete transactions asociated with this person as dest
				for t in person.accountmodel_reference_dest_set: 
					t.delete()
				# delete all membership definitions
				for m in person.member_set:
					m.delete()
				# finally delete the person self
				person.delete()
			# list persons
			self.listGroups(project, Person, None)
		
		elif action=='person_rename':
			# rename an account
			account = Account.get(self.request.get('account'));
			account.name=self.request.get('name', account.name)
			account.put()
			# list accounts
			self.listGroups(project, Person, account)

		elif action=='group_rename':
			# rename an account
			account = Account.get(self.request.get('account'));
			account.name=self.request.get('name', account.name)
			account.put()
			# list accounts
			self.listGroups(project, Group, account)		
			
		elif action=='group_remove':
			# remove a group
			group = Group.get(self.request.get('group'));
			# delete transactions asociated with this group as source
			for t in group.accountmodel_reference_source_set: 
				t.delete()
			# delete transactions asociated with this group as dest
			for t in group.accountmodel_reference_dest_set: 
				t.delete()
			# delete all membership definitions
			for m in group.member_set:
				m.delete()
			# finally delete the group self
			group.delete()			
			# list remaining groups
			self.listGroups(project, Group, None)
			
		elif action=='members':
			# list members of a group
			for member in Group.get(self.request.get('group')).member_set:
				self.response.out.write('<option value="%(value)s">%(name)s: %(weight)f</option>' % {'name':member.person.name, 'value':member.key(), 'weight': member.weight })
		
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})

	def	get(self):
		(project, right)=self.getandcheckproject(1)
		self.generate('accounts', {
			'project': project,
			'project_key': project.key(),
		})

# ******************************************************************************
# ** ACTUAL HANDLERS ***********************************************************
# ******************************************************************************
class AccessHandler(BaseRequestHandler):
	def	post(self):
		(project, right)=self.getandcheckproject(1)
		action = self.request.get('action','list')
		if action=='invite':	
			i = Invitation(project=project, user=users.User(email=self.request.get('email')), right=int(self.request.get('right')), code=random.randint(0, 2<<31))
			i.put()
			message = mail.EmailMessage(sender=users.get_current_user().email(),
										subject="Invitation to Urlaubsabrechnung")
			message.to = i.user.email()
			message.body = "Hallo!\n\nDu bist eingeladen die Abrechnung fuer %(projectname)s anzusehen.\n\n" \
			"Bitte melde dich unter\nhttp://urlaubsabrechnung.appspot.com/join?invitation=%(invitation)s&code=%(code)d"\
			"\nmit einem google account an.!" % {
													'projectname':  project.name,
													'invitation':  i.key(),
													'code': i.code
												}
			message.send()
			# generate std output
			self.get()
			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
			
	def	get(self):
		(project, right)=self.getandcheckproject(1)
		self.generate('access', {
			'project': project,
			'project_key': project.key(),
			'rights': [
				{
					'user': right.user,
					'right': right.right,
					'key': right.key(),
				} for right in project.projectrights_set
			],
			'invitations': [
				{
					'user': invitation.user,
					'right': invitation.right,
					'created': invitation.created,
					'key': invitation.key(),
				} for invitation in project.invitation_set
			]
		})

class JoinHandler(webapp.RequestHandler):
	@login_required
	def	get(self):
		try:
			i = Invitation.get(self.request.get('invitation', '0'))
			if i is None:
				self.redirect("/")
				return
			if int(self.request.get('code', 0))==i.code:
				# check for existiting access to project
				rights = ProjectRights.gql("WHERE user=:user and project=:project", user=users.get_current_user(), project=i.project).get()
				# edit rights
				if not rights:
					rights = ProjectRights(project=i.project, user=users.GetCurrentUser(), right=i.right)
				# possibly upgrade rights
				if rights.right<i.right:
					rights.right = i.right
				rights.put()
				# delete invitation
				i.delete()
			# redirect to project list
			self.redirect("/")
		except BadKeyError:
			self.redirect("/")
			return 
		
# ******************************************************************************
# ** ACTUAL HANDLERS ***********************************************************
# ******************************************************************************
class CurrenciesHandler(BaseRequestHandler):
	def	post(self):
		(project, right)=self.getandcheckproject(1)
		action = self.request.get('action','list')
		if action=='list':
			# add base currency of project
			self.response.out.write('<option value="%(value)s">%(name)s</option>' % {'value':None, 'name':project.currency})
			# create a list of options against all accounts
			for a in project.currency_set:
				self.response.out.write('<option value="%(value)s">%(name)s</option>' % {'name':a.name, 'value':a.key()})
		
		elif action=='add':
			# add a new currency
			Currency(project=project, name=self.request.get('name'), divisor=float(self.request.get('divisor', '1'))).put()
			# generate std output
			self.get()

		elif action=='delete':
			# delete existing currency
			c = Currency.get(self.request.get('key'))
			for t in c.transaction_set:
				t.delete()
			c.delete()
			# generate std output
			self.get()
			
		elif action=='update':
			# update existing currency
			c = Currency.get(self.request.get('key'))
			c.name = self.request.get('name', c.name)
			c.divisor = float(self.request.get('divisor', c.divisor))
			c.put()
			# generate std output
			self.get()
			
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})
		
	def	get(self):
		(project, right)=self.getandcheckproject(1)
		self.generate('currencies', {
			'project': project,
			'project_key': project.key(),
			'currencies': [
				{
					'name': currency.name,
					'divisor': currency.divisor,
					'key': currency.key(),
				} for currency in project.currency_set]
		})
			
# ******************************************************************************
# ** ACTUAL HANDLERS ***********************************************************
# ******************************************************************************
class ProjectsHandler(BaseRequestHandler):
	def	get(self):
		if self.checklogin():
			return;
		self.generate('projects', {
			'projects':  [{'name': right.project.name, 'canedit':right.right>1, 'id':right.project.key()} for right in ProjectRights.gql("WHERE user=:user AND right>0", user=users.get_current_user())],
		})
	
	def	post(self):
		if not users.GetCurrentUser():
			self.response.out.write(users.CreateLoginURL("/"))
			return;
		action = self.request.get('action','add')
		if action=='add':
			# create the project and return the new location to go to
			project = Project(name=self.request.get('name'), currency=self.request.get('currency'))
			project.put()
			# add access rights for this user to the new project
			rights = ProjectRights(project=project, user=users.GetCurrentUser(), right=255)
			rights.put()
			# redirect to summary
			self.response.out.write("/summary?project=%(key)s" % {'key':project.key()})
		elif action=='delete':
			# remove me from the projects right list
			project = Project.get(self.request.get('project',''))
			if (not project):
				raise Exception("Unknown project!")
			# check rights of current user for this project, and deny access if not permitable
			rights = ProjectRights.gql("WHERE user=:user and project=:project", user=users.get_current_user(), project=project).get()
			if rights:
				rights.delete()
			# redirect to my page
			self.response.out.write("/")
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})

# ******************************************************************************
# ** ACTUAL HANDLERS ***********************************************************
# ******************************************************************************
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
		
# ******************************************************************************
# ** ACTUAL HANDLERS ***********************************************************
# ******************************************************************************
class ReportHandler(BaseRequestHandler):
	@login_required
	def get(self):
		user = users.get_current_user()
		self.response.out.write('<h1>Projects</h1><p>User: %(user)s<ul></p>' % {'user':user})
		for right in ProjectRights.gql("WHERE user=:user", user=user):
			project=right.project
			self.response.out.write('<li>Transactions: <a href="/transactions?project=%(key)s">%(name)s</a></li>' % {'name':project.name, 'key':project.key()})
			self.response.out.write('<h2>Accounts</h2><ul>')	
			for account in project.person_set:
				if isinstance(account, Person):
					self.response.out.write('<li>Person: %(name)s</li>' % {'name':account.name})
				elif isinstance(account, Group):
					self.response.out.write('<li>Group: %(name)s<br/>Members<ul>' % {'name':account.name})
					for member in account.member_set:
						self.response.out.write('<li>%(weight)gx%(name)s</li>' % {'name':member.person.name, 'weight':member.weight})
					self.response.out.write('</ul></li>')
				else:
					self.response.out.write('<li>Other: %(name)s</li>' % {'name':account.name})
			self.response.out.write('</ul>')
			self.response.out.write('<h2>Transactions</h2><ul>')	
			for transaction in project.transaction_set:
				if transaction.currency:
					c = transaction.currency.name
					d =  transaction.currency.divisor
				else:
					c = project.currency
					d = float(1)
				self.response.out.write('<li>%(source)s gives %(ammount).2f%(currency)s (%(pammount).2f%(punit)s) to %(dest)s for "%(text)s"</li>' %
					{'source': transaction.source.name,  
					'ammount': transaction.ammount,  
					'currency': c, 
					'pammount': transaction.ammount/d,
					'punit': project.currency,
					'dest': transaction.dest.name,
					'text': transaction.text
					})
			self.response.out.write('</ul>')

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
			
			self.response.out.write('<h1>Results</h1>')
			self.response.out.write(res.getvalue())			
			
# ******************************************************************************
# ** ACTUAL HANDLERS ***********************************************************
# ******************************************************************************
class AddData(BaseRequestHandler):
	def get(self):
		slovenien = Project(name="Slovenien", currency="EUR")
		slovenien.put()
		daniel = Person(project=slovenien, name="Daniel")
		daniel.put()
		julia = Person(project=slovenien, name="Julia")
		julia.put()
		alle = Group(project=slovenien, name="Alle")
		alle.put()		
		Member(group=alle, person=daniel, weight=float(1)).put()
		Member(group=alle, person=julia, weight=float(2)).put()
		ProjectRights(project=slovenien, right=3, user=users.get_current_user()).put()
		rubel=Currency(project=slovenien, name="Rubel", divisor=float(28)).put()
		# add some transactions
		Transaction(project=slovenien, source=daniel, dest=julia, ammount=float(500), currency=rubel, text='das Kleidchen').put()
		Transaction(project=slovenien, source=julia, dest=alle, ammount=float(32), text='Essen Flughafen').put()
		Transaction(project=slovenien, source=daniel, dest=alle, ammount=float(334), currency=rubel, text='Konfekt').put()
		# done
		self.response.out.write('Added')

class JsonTest(BaseRequestHandler):
	def get(self):
		if self.checklogin():
			return
		self.generate('jsontest', {})
	
	def	post(self):
		if not users.GetCurrentUser():
			self.response.out.write(users.CreateLoginURL("/"))
			return;
		self.response.out.write(json.dumps(
		{
			'projects':  [{'name': right.project.name, 'canedit':right.right>1, 'id':str(right.project.key())} for right in ProjectRights.gql("WHERE user=:user AND right>0", user=users.get_current_user())],
		}))
		
# ******************************************************************************
# ** URL Mapping and MAIN routine **********************************************
# ******************************************************************************
application = webapp.WSGIApplication([
  ('/'				, ProjectsHandler),
  ('/summary'		, SummaryHandler),
  ('/transactions'	, TransactionsHandler),
  ('/currencies'	, CurrenciesHandler),
  ('/accounts'		, AccountsHandler),
  ('/report'		, ReportHandler),
  ('/access'		, AccessHandler),
  ('/join'			, JoinHandler),
  # debug/internal
  ('/add'			, AddData),
  ('/json'			, JsonTest),
 ], debug=_DEBUG)

def main():
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
