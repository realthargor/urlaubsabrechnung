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
		# generate output
		self.generate('summary', {
			'project': project,
			'project_key': project.key(),
			'transactions': project.TransactionTable(),
			'groups': project.GroupDefList(),
			'currencies': project.CurrencyDefList()
		})
