#!/usr/bin/env python
# ******************************************************************************
# ** DATA MODELS ***************************************************************
# ******************************************************************************

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.db import polymodel
import Security 

class Project(db.Model):
    name = db.StringProperty() # default name for all new users
    currency = db.StringProperty()
    state = db.IntegerProperty(default=0) # 0..open, 1..closing, 2..closed
        
    """ returns all list of all projects the user actually has rights for """
    @staticmethod
    def list():
        projects = []
        for right in ProjectRights.gql("WHERE user=:user AND right>0", user=users.get_current_user()):
			right.project.rights = right.right
			# append users display name
			right.project.display_name = right.local_name + " (" +  right.project.name + ")" if right.local_name and right.local_name != '' else right.project.name
			projects.append(right.project)
        return projects
    
    """ returns all list of ALL projects """
    @staticmethod
    def listAll():                
        projects = []
        # super user sees all projects
        if users.is_current_user_admin():
            for p in Project.all():
                p.rights = 65535
                projects.append(p)
        return projects
    
    """ returns true, when the user is allowed to view the project report """    
    def RightView(self):
        return self.rights >= Security.Right_View

    """ returns true, when the user is allowed to edit the project """    
    def RightEdit(self):
        return self.rights >= Security.Right_Edit;
    
    """ returns true, when the user is allowed to edit the project """    
    def RightManage(self):
        return self.rights >= Security.Right_Manage;
    
    """ returns true, when the user is allowed to edit the project """    
    def RightOwner(self):
        return self.rights >= Security.Right_Owner;
        
    """ returns a list of endpoint accounts """
    def Endpoints(self):
        return filter(lambda a: a.IsEndpoint(), self.person_set)
        
    """ checks weather the given name is a valid new name for a a new account or a given existing account """
    def CheckNewAccountName(self, name, account=None):
        if len(name) < 1:
            raise Exception("account name must be at least on character long")
        for a in self.person_set:
            if a.name == name and (account == None or a.key() != account.key()):
                raise Exception("duplicate name")
                                    
    """ defines accounts and transactions members for the project summary report """
    def CalculateResult(self):
        # GROUPS         
        self.groups = dict()
        for g in filter(lambda a: not a.IsEndpoint(), self.person_set):
            g.sum = 0
            g.credit = 0
            g.debit = 0
            for member in g.member_set:
                g.sum+=abs(member.weight)
            g.members = []
            for member in g.member_set:
                person = member.person
                person.weight=abs(member.weight)
                person.part=100*person.weight/g.sum
                g.members.append(person)
            self.groups[str(g.key())] = g;
        # PERSONS
        self.persons = dict()
        for person in sorted(self.Endpoints(), cmp=lambda x, y: cmp(x.name, y.name)):
            person.sum=0
            person.credit=0
            person.debit=0
            self.persons[str(person.key())]=person
        # TRANSACTIONS
        self.transactions = [];
        for transaction in sorted(self.transaction_set, cmp=lambda x, y: cmp(x.date, y.date)):
            # add up credit sum, for persons/groups
            if transaction.source.IsEndpoint():
                self.persons[str(transaction.source.key())].credit+=transaction.AmountBase()
            else:
                self.groups[str(transaction.source.key())].credit+=transaction.AmountBase()
            # add up debit sum, for persons/groups
            if transaction.dest.IsEndpoint():
                self.persons[str(transaction.dest.key())].debit+=transaction.AmountBase()
            else:
                self.groups[str(transaction.dest.key())].debit+=transaction.AmountBase()
            # update list of affected persons    
            affected = transaction.UpdateSums(balance=dict())
            transaction.affected = [{
                                    'value':affected.get(endpoint.key(), 0), 
                                       'negative':affected.get(endpoint.key(), 0)<0,
                                       'positive':affected.get(endpoint.key(), 0)>0,
                                       } for endpoint in self.persons.values()];
            for (key, value) in affected.iteritems():
                self.persons[str(key)].sum+=value
            self.transactions.append(transaction)
        # GROUPS
        for group in self.groups.values():
            group.credit_minus_debit = group.credit - group.debit
        # PERSONS
        for person in self.persons.values():
			person.sum_negative = person.sum<=-0.005
			person.sum_positive = person.sum>=+0.005
			person.group_part = person.sum - (person.credit - person.debit)
                    
class Account(polymodel.PolyModel):
    name = db.StringProperty(required=True)
    def IsEndpoint(self):
        return isinstance(self, Person) or sum([abs(member.weight) for member in self.member_set]) == 0    
        
    """ return the sum of weights for the given group """
    def SumOfMemberWeigths(self):
        return sum([abs(member.weight) for member in self.member_set]) if isinstance(self, Group) else 0

    """ Calculates which final accounts are affected by an enquire to the given account """
    def enquire(self, amount, balance=dict(), sign=1):
        # make sure the amount is rounded
        amount = round(amount, 2)
        # calculate the sum of weights
        sweight = self.SumOfMemberWeigths()
        # when the weight sum is zero, that means, there are no valid members, thus we map that to the account
        if sweight == 0:
            balance[self.key()] = balance.get(self.key(), 0) + sign * amount;
            return balance
        # now we create a dictionary
        ramount = amount        # remaing amount
        rweight = sweight        # remaing sum of weights
        # walk through the sorted list, the last member (the one with the largest weight) gets the remaining sum
        for member in sorted(self.member_set, cmp=lambda x, y: cmp(x.weight, y.weight)):
            rweight -= abs(member.weight)
            val = round(amount * abs(member.weight) / sweight, 2) if rweight > 0 else ramount
            ramount -= val
            balance[member.person.key()] = balance.get(member.person.key(), 0) + sign * val
        # return dictionary again
        return balance
        
    """ returns the number of transactions affected by deleting this Account """
    def ByDeleteAffectedTransactions(self):
        return len(self.accountmodel_reference_source_set) + len(self.accountmodel_reference_dest_set)
        
    """ overwrites polymodel.PolyModel.delete() and also deletes all references """
    def delete(self):
        # delete transactions asociated with this person as source
        for t in self.accountmodel_reference_source_set:
            t.delete()
        # delete transactions asociated with this person as dest
        for t in self.accountmodel_reference_dest_set: 
            t.delete()        
        # call base method (which actually deletes this instance from the data store)
        polymodel.PolyModel.delete(self)

class Person(Account):
    project = db.ReferenceProperty(Project)
    """ overwrites polymodel.PolyModel.delete() and also deletes all references """
    def delete(self):
        # delete all membership definitions
        for membership in self.member_set:
            membership.delete()
        # call base method (which actually deletes this instance from the data store)
        Account.delete(self)

class Group(Account):
    project = db.ReferenceProperty(Project)
    
    """ overwrites polymodel.PolyModel.delete() and also deletes all references """
    def delete(self):
        # delete all membership definitions
        for membership in self.member_set:
            membership.delete()
        # call base method (which actually deletes this instance from the data store)
        Account.delete(self)
    
class Member(db.Model):
    group = db.ReferenceProperty(Group)
    person = db.ReferenceProperty(Person)
    weight = db.FloatProperty()    

class Currency(db.Model):
    project = db.ReferenceProperty(Project)
    name = db.StringProperty()
    factor = db.FloatProperty(default=1.0)
    divisor = db.FloatProperty(default=1.0)

class Transaction(db.Model):
    project = db.ReferenceProperty(Project)
    source = db.ReferenceProperty(Account, collection_name="accountmodel_reference_source_set")
    dest = db.ReferenceProperty(Account, collection_name="accountmodel_reference_dest_set")
    ammount = db.FloatProperty()
    currency = db.ReferenceProperty(Currency)
    text = db.StringProperty()  
    date = db.DateTimeProperty(auto_now_add=True)
    user = db.UserProperty(auto_current_user=True)
    check = db.BooleanProperty(default=False)
    lastmod = db.DateTimeProperty(auto_now=True)
    
    """ returns the amount of the transaction using in the project currency """
    def AmountBase(self):
        return self.ammount * self.currency.factor / self.currency.divisor if self.currency else self.ammount
    
    """ returns the currency text """
    def CurrencyName(self):
        return self.currency.name if self.currency else self.project.currency
            
    def UpdateSums(self, balance=dict()):
        self.dest.enquire(amount=self.AmountBase(), balance=balance, sign= -1)
        self.source.enquire(amount=self.AmountBase(), balance=balance, sign= +1)
        return balance

class ProjectRights(db.Model):
    project = db.ReferenceProperty(Project, required=True)
    user = db.UserProperty(required=True)
    right = db.IntegerProperty()
    local_name = db.StringProperty(default="")
    
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
    created = db.DateTimeProperty(auto_now_add=True)  

"""
    A Ticket is anonymous way to access a project for a given time
""" 
class Ticket(db.Model):
    project = db.ReferenceProperty(Project, required=True)
    right = db.IntegerProperty(required=True)
    code = db.IntegerProperty(required=True)
    expires = db.DateTimeProperty()
    user = db.UserProperty()
    local_name = db.StringProperty(default="")
