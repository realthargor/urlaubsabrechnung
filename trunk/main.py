#!/usr/bin/env python
import wsgiref.handlers

from google.appengine.ext import webapp
from ProjectsHandler import ProjectsHandler
from SummaryHandler import SummaryHandler
from TransactionsHandler import TransactionsHandler
from CurrenciesHandler import CurrenciesHandler
from AccountsHandler import AccountsHandler
from AccessHandler import AccessHandler
from JoinHandler import JoinHandler

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
