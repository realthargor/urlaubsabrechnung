#!/usr/bin/env python

import Security
from BaseRequestHandler import BaseRequestHandler
                                
class HelpHandler(BaseRequestHandler):
    @Security.ProjectAccess(Security.Right_None)
    def	get(self):
        self.generate('help')
        pass