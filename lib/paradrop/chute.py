###################################################################
# Copyright 2013-2014 All Rights Reserved
# Authors: The Paradrop Team
###################################################################

from lib.paradrop import *
from lib.paradrop.pderror import PDError
from lib.paradrop.utils import pdutils

STATE_INVALID = "invalid"
STATE_DISABLED = "disabled"
STATE_RUNNING = "running"
STATE_FROZEN = "frozen"
STATE_STOPPED = "stopped"

class Chute:
    """
        Wrapper class for Chute objects.
    """

    def __init__(self, name="", guid="", apid="", contact="", state="", internalid="", devinfo={}, descriptor=None):
        # Set these first so we don't have to worry about it later
        self.name = name
        self.guid = guid
        self.apid = apid
        self.contact = contact
        self.state = state
        self.internalid = internalid
        self.devinfo = devinfo
        self.struct = {}
        self.runtime = []
        self.traffic = []
        self.resource = {}
        self.files = []
        self._cache = {}
        
        # Descriptor will be a dict object of potentially ALL of the chute options
        if(descriptor):
            if(type(descriptor) is not dict):
                out.warn('** %s Unable to parse descriptor, not dict type\n' % logPrefix())
                return
            self.setObject('name', descriptor)
            self.setObject('guid', descriptor)
            self.setObject('apid', descriptor)
            self.setObject('contact', descriptor)
            self.setObject('state', descriptor)
            self.setObject('internalid', descriptor)
            self.setObject('devinfo', descriptor, dict)
            self.setObject('struct', descriptor, dict)
            self.setObject('runtime', descriptor, list)
            self.setObject('traffic', descriptor, list)
            self.setObject('resource', descriptor, dict)
            self.setObject('files', descriptor, list)
            if('cache' in descriptor):
                self.loadCache(descriptor['cache'])
                

    def setObject(self, attr, data, jsonize=None):
        # This if block can fail, its ok the descriptor doesn't have to contain everything
        if(attr in data.keys()):
            # Pull out the data from the dict
            d = data[attr]
            # See if we need to convert this to a JSON object before setting it
            if(jsonize and type(d) is not jsonize and d):
                try:
                    d = str2json(d)
                except:
                    out.warn('** %s Unable to jsonize data: %s\n' % (logPrefix(), d))
            setattr(self, attr, d)

    def __repr__(self):
        return "<Chute %s:%s (%s) - %s>" % (self.name, self.internalid, self.guid, self.state)
    
    def __str__(self):
        s = "%s:c%s (%s) - %s\n" % (self.name, self.internalid, self.guid, self.contact)
        if(self.state != ""):
            s += "  state:    %s\n" % self.state
        if(self.apid != ""):
            s += "  apid:     %s\n" % self.apid
        if(self.devinfo is not None):
            s += "  devinfo:  %s\n" % str(self.devinfo)
        if(self.struct is not None):
            s += "  struct:   %s\n" % str(self.struct)
        else:
            s += "  struct:   NONE\n"
        if(self.runtime is not None):
            s += "  runtime:  %s\n" % str(self.runtime)
        else:
            s += "  runtime:  NONE\n"
        if(self.traffic is not None):
            s += "  traffic:  %s\n" % str(self.traffic)
        else:
            s += "  traffic:  NONE\n"
        if(self.resource is not None):
            s += "  resource: %s\n" % str(self.resource)
        else:
            s += "  resource: NONE\n"
        if(self.files is not None):
            s += "  files:  %s\n" % str(self.files)
        else:
            s += "  files:  NONE\n"
        return s

    def getAPIFormat(self):
        """Return a dict object of all the data in the Chute, formatted to be sent to the API server."""
        return {'name': self.name, 'guid': self.guid, 'contact': self.contact, 'devinfo': self.devinfo}
    
    def getAPIDataFormat(self, noAdd=None):
        """
            Return a dict object of all the data in the Chute that is public, formatted to be sent to the API server.
            Arguments:
                [noAdd] : a list of keys not to add as output (used for storing manifest files)
        """
        # Generate the full list
        d = {'name': self.name, 'apid': self.apid, 'guid': self.guid, 'state': self.state, 'internalid': self.internalid,
                'struct': self.struct, 'runtime': self.runtime, 'traffic': self.traffic, 'devinfo': self.devinfo, 'contact': self.contact,
                'resource': self.resource, 'files': self.files}
        # If they say so, remove some things
        if(noAdd):
            for k in noAdd:
                try:
                    del(d[k])
                except:
                    pass
        return d

    def fullDump(self):
        """Return a dump of EVERYTHING in this chute including all API data and all internal cache data."""
        d = self.getAPIDataFormat()
        d['cache'] = self._cache
        return d

    def loadCache(self, c):
        """Loads the cache object provided into the internal _cache object."""
        if(not isinstance(c, dict)):
            c = str2json(c)
        self._cache = c

    def decodeInfo(self):
        """Return a string (not UNICODE) of the devinfo object"""
        return json2str(self.devinfo)

    def isValid(self):
        """Return True only if the Chute object we have has all the proper things defined to be in a valid state."""
        if(not self.name or len(self.name) == 0):
            return False
        if(not self.guid or not pdutils.isGuid(self.guid)):
            return False
        if(not self.internalid or len(self.internalid) != 4):
            return False
        if(not isinstance(self.struct, dict)):
            return False
        if(not isinstance(self.runtime, list)):
            return False
        if(not isinstance(self.traffic, list)):
            return False
        if(not isinstance(self.resource, dict)):
            return False
        if(not isinstance(self.files, list)):
            return False
        return True

    def getInternalName(self):
        """Return the internal name we use "c####" based on the internalid defined."""
        return "c%s" % self.internalid
    
    def delCache(self, key):
        """Delete the key:val from the _cache dict object."""
        if(key in self._cache.keys()):
            del(self._cache[key])
    
    def setCache(self, key, val):
        """Set the key:val into the _cache dict object to carry around."""
        self._cache[key] = val

    def getCache(self, key):
        """Get the val out of the _cache dict object, or None if it doesn't exist."""
        return self._cache.get(key, None)

    def dumpCache(self):
        """
            Return a string of the contents of this chute's cache.
            In case of catastrophic failure dump all cache content so we can debug.
        """
        return "\n".join(["%s:%s" % (k,v) for k,v in self._cache.iteritems()])
    
    def appendCache(self, key, val):
        """
            Finds the key they requested and appends the val into it, this function assumes the cache object
            is of list type, if the key hasn't been defined yet then it will set it to an empty list.
        """
        r = self.getCache(key)
        if(not r):
            r = []
        elif(not isinstance(r, list)):
            out.warn('** %s Unable to append to cache, not list type\n' % logPrefix())
            return
        r.append(val)
        self.setCache(key, r)
    
    def merge(self, ch1, chCat=None, avoid=[]):
        # Use a dict to make this work
        if(isinstance(ch1, Chute)):
            ch1 = ch1.getAPIDataFormat()
            
        for k,v in ch1.iteritems():
            try:
                if(hasattr(self, k)):
                    if(((chCat and chCat == k) or not chCat) and (k not in avoid)):
                        setattr(self, k, v)
                else:
                    out.warn('** %s Chute attribute: %s not found\n' % (logPrefix(), k))
            except:
                out.warn('** %s Error adding Chute attribute: %s\n' % (logPrefix(), k))

def loadManifest(chPath, theChute, chCat=None):
    """
        Loads a manifest from the specified file location into a Chute object.
        Arguments:
            @chPath : the path to the manifest file
            @theChute : the chute to add to, if None then do a new Chute
            @chCat : the category to pull from, if None then pull everything
        Returns:
            A Chute object loaded based on manifest definition
            None if missing or error in syntax
    """
    import os
    if(not os.path.exists(chPath)):
        out.err('!! %s Missing path: %s\n' % (logPrefix(), chPath))
        return None
    s = ""
    with open(chPath, 'r') as fd:
        while(True):
            line = fd.readline().rstrip()
            if(not line):
                break
            s += line
    
    # Convert str to json
    try:
        c = str2json(s)
    except Exception as e:
        out.err('!! %s Error loading chute data: %s\n' % (logPrefix(), str(e)))
        return None
    if(not theChute):
        theChute = Chute()

    theChute.merge(c, chCat)
    return theChute

def storeManifest(ch, chPath):
    """
        Stores a manifest based on the chute provided to the location specified.
        Arguments:
            @ch : the Chute object
            @chPath : the path to the manifest file
        Returns:
            True in failure
            False otherwise
    """
    import os, json
    if(os.path.exists(chPath)):
        out.info('-- %s Manifest exists, overwriting\n' % (logPrefix()))
    try:
        s = json.dumps(ch.getAPIDataFormat(), sort_keys=True, indent=4, separators=(',', ': '))
        fd = open(chPath, 'w')
        fd.write(s)
        fd.flush()
        fd.close()
        return False
    except:
        return True
