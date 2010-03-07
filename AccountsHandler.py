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
						
class AccountsHandler(BaseRequestHandler):
	def listGroups(self, type, default=None):
		# list remaining groups
		for a in self.project.person_set:
			if isinstance(a, type):
				if default==None or default.key()==a.key():
					self.response.out.write('<option selected value="%(value)s">%(name)s</option>' % {'name':a.name, 'value':a.key()})
					default=a	# this prevents from getting default again
				else:
					self.response.out.write('<option value="%(value)s">%(name)s</option>' % {'name':a.name, 'value':a.key()})
		
	def	post(self):
		self.updateproject()
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
			self.listGroups(type=target_class)
		
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
				Member(project=self.project, group=group, weight=member_weight, person=Person.get(a)).put()
			# delete all members with weight 0
			for member in Group.get(self.request.get('group')).member_set:
				if member.weight == 0:
					member.delete()
			# list members of a group
			for member in Group.get(self.request.get('group')).member_set:
				self.response.out.write('<option value="%(value)s">%(name)s: %(weight)f</option>' % {'name':member.person.name, 'value':member.key(), 'weight': member.weight })
				
		elif action=='group_add':
			# add a new group
			newname = self.request.get('name')
			self.project.CheckNewAccountName(newname)
			group = Group(name=newname, project=self.project)
			group.put()
			# list new remaining groups
			self.listGroups(type=Group, default=group)
			
		elif action=='person_add':
			# add a new person
			newname = self.request.get('name')
			self.project.CheckNewAccountName(newname)
			person = Person(name=newname, project=self.project)
			person.put()
			# list the persons
			self.listGroups(type=Person, default=person)
			
		elif action=='person_remove':
			# remove a list of persons
			for person_key in json.loads(self.request.get('person_list')):
				Account.get(person_key).delete()
			# list persons
			self.listGroups(type=Person)
		
		elif action=='person_rename':
			# rename an account
			account = Account.get(self.request.get('account'));
			newname = self.request.get('name', account.name)
			self.project.CheckNewAccountName(newname, account)
			account.name = newname
			account.put()
			# list accounts
			self.listGroups(type=Person, default=account)

		elif action=='group_rename':
			# rename an account
			account = Account.get(self.request.get('account'));
			newname = self.request.get('name', account.name)
			self.project.CheckNewAccountName(newname, account)
			account.name = newname
			account.put()
			# list accounts
			self.listGroups(type=Group, default=account)		
			
		elif action=='group_remove':
			# remove a group
			Group.get(self.request.get('group')).delete();
			# list remaining groups
			self.listGroups(type=Group)
			
		elif action=='members':
			# list members of a group
			for member in Group.get(self.request.get('group')).member_set:
				self.response.out.write('<option value="%(value)s">%(name)s: %(weight)f</option>' % {
					'name':member.person.name, 
					'value':member.key(), 
					'weight': member.weight 
				})
		
		else:
			raise Exception("Unknown action '%(action)s'!" % {'action':action})

	def	get(self):
		self.updateproject()
		self.generate('accounts')
