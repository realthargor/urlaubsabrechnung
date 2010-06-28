#!/usr/bin/env python

from BaseRequestHandler import BaseRequestHandler
                                
class HelpHandler(BaseRequestHandler):
    def	get(self):
        self.updateproject()
        self.generate('help')
        pass