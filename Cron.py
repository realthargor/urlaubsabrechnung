#!/usr/bin/env python
import wsgiref.handlers

from google.appengine.ext import webapp
from CronDeleteProjectsHandler import CronDeleteProjectsHandler

# ******************************************************************************
# ** URL Mapping and MAIN routine **********************************************
# ******************************************************************************
application = webapp.WSGIApplication([
  ('/cron/deleteprojects'		, CronDeleteProjectsHandler),
 ], debug=True)

def main():
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
	main()
