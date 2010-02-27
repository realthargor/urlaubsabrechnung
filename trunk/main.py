#!/usr/bin/env python
import os
import cgi
import wsgiref.handlers

from google.appengine.ext import webapp

from models import *
from BaseRequestHandler import BaseRequestHandler
from ProjectsHandler import *
from SummaryHandler import *
from TransactionsHandler import *
from CurrenciesHandler import *
from AccountsHandler import *
from AccessHandler import *
from JoinHandler import *
											
# ******************************************************************************
# ** URL Mapping and MAIN routine **********************************************
# ******************************************************************************
application = webapp.WSGIApplication([
  ('/'				, ProjectsHandler),
  ('/summary'		, SummaryHandler),
  ('/transactions'	, TransactionsHandler),
  ('/currencies'	, CurrenciesHandler),
  ('/accounts'		, AccountsHandler),
  ('/access'		, AccessHandler),
  ('/join'			, JoinHandler),
 ], debug=True)

def main():
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
