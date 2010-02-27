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
