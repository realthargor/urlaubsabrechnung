'''
Created on 18.07.2010

@author: Daniel
'''
from google.appengine.api import users
from datetime import datetime
import models

Right_None = 0
Right_View = 100
Right_Edit = 200
Right_Manage = 500
Right_Owner = 1000
Right_Admin = 9999

def ProjectAccess(requested_permission):
    def wrapper(handler_method):
        def check_login(self, *args):
            self.project = None
            self.user = users.get_current_user()
            self.project_list_enabled = self.user != None 
            # a project key is required
            self.accesss_key = self.request.get('project', '')        
            if self.accesss_key=='':
                # no project is specified redirect to main url
                if requested_permission>Right_None:
                    self.redirect("/")
                    return
            else:            
                # first we check if the project key is a  "anonymous" ticket, we use this as
                # we can see this, by splitting the project key at '_'
                ticket_data = self.accesss_key.split('_',2)
                if len(ticket_data)==2:
                    ticket = models.Ticket.get(ticket_data[0])
                    # check code
                    if ticket.code!=int(ticket_data[1]):
                        raise Exception("Ticket invalid!")
                    if datetime.today()>ticket.expires:
                        raise Exception("Ticket expired!")
                    self.project = ticket.project;
                    self.project.rights = Right_Admin if users.is_current_user_admin() else ticket.right
                    self.user = ticket.user
                    self.project.local_name = ticket.local_name
                else:                    
                    self.project = models.Project.get(self.accesss_key)
                    # now we need login information to check any further rights
                    self.user = users.get_current_user()
                    if not self.user:
                        # we are not logged in -> redirect to login URI, but append project if the method has been other than get
                        self.redirect(users.create_login_url(self.request.uri+("?project="+self.accesss_key if self.request.method!='GET' else '')))
                        return
                    # we are logged in query for user project settings
                    settings = models.ProjectRights.gql("WHERE user=:user and project=:project", user=self.user, project=self.project).get();
                    self.project.rights = Right_Admin if users.is_current_user_admin() else settings.right if settings else Right_None
                    # replace project name with local name                
                    self.project.local_name = settings.local_name if settings else None;
            # setup display name
            if self.project:                
                self.project.display_name = self.project.local_name if self.project.local_name and self.project.local_name!='' else self.project.name                                                 
                # check rights and call original handler
                if self.project.rights<requested_permission:
                    raise Exception("Permission denied!")
            handler_method(self, *args)
            pass                
        return check_login
    return wrapper 