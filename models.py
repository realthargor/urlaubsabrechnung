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
