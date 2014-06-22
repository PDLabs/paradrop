###################################################################
# Copyright 2013-2014 All Rights Reserved
# Authors: The Paradrop Team
###################################################################
import json

from lib.paradrop import *
from lib.paradrop.utils import pdutils
from lib.paradrop.pderror import PDError

REQUIRED_AP_KEYS = ["name", "guid"]


class AP:
    """
        Wrapper class for AP objects.
    """

    def __init__(self, name="", guid="", contact="", devinfo={}, descriptor=None):
        self.name = name
        self.guid = guid
        self.contact = contact
        self.devinfo = devinfo
        
        if(descriptor):
            self.setObject('name', descriptor)
            self.setObject('guid', descriptor)
            self.setObject('contact', descriptor)
            self.setObject('devinfo', descriptor, dict)
    
    def setObject(self, attr, data, jsonize=None):
        if(attr in data.keys()):
            d = data[attr]
            # See if we need to convert this to a JSON object before setting it
            if(jsonize and type(d) is not jsonize and d):
                d = json.loads(d)
            setattr(self, attr, d)

    def __str__(self):
        return "%s (%s)\n  %s\n  %s" % (self.name, self.guid, self.contact, str(self.devinfo))
    
    def __repr__(self):
        return "<AP %s (%s)>" % (self.name, self.guid)

    def getAPIFormat(self):
        """Return a dict object of all the data in the AP, formatted to be sent to the API server."""
        return {'name': self.name, 'guid': self.guid, 'contact': self.contact, 'devinfo': self.devinfo}

    def decodeInfo(self):
        """Return a string (not UNICODE) of the devinfo object"""
        return json2str(self.devinfo)
