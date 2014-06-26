###################################################################
# Copyright 2013-2014 All Rights Reserved
# Authors: The Paradrop Team
###################################################################

import urllib2, sys, time, json, base64, mmap, os, md5

from lib.paradrop import *
from lib.paradrop.ap import AP
from lib.paradrop.chute import Chute
from lib.paradrop.utils import pdutils
from lib.paradrop.api import pdapi
from lib.paradrop.api.pdapi import PDAPIError

APISERVER = 'http://paradrop.org:10000/v1/'

class ParaDropAPIClient:
    """
        Stub class to gain access to ParaDrop API server.
            Arguments:
                @uname:        username of the developer
                @passwd:       cleartext password of the developer
                @devid:        UUID associated with developers account, if unknown it is looked up via API
                @sessionToken: the most recent sessionToken for this user, if None then one is Authorized via API
    """
    def __init__(self, uname='', passwd='', devid=None, sessionToken=None, url=APISERVER):
        self.uname = uname
        self.passwd = md5.new(passwd).hexdigest()
        self.devid = devid
        self.tok = sessionToken
        self.baseUrl = url

    def buildHeaders(self, fileName="", c_size=0):
        """Uses the member variables of this object to build the correct header.
            All headers utilize the same components unless a file is being PUT on the server."""
        
        # If a file is what we are sending
        if(fileName != ""):
            h = {'Accept': 'application/json', 'Content-Type':'TODO', 'CSize': c_size}
        # Otherwise, build header based on known components
        else:
            h = {'Accept': 'application/json', 'Content-Type':'application/json'}
        
        if(self.devid):
            h['devid'] = self.devid
        if(self.tok):
            h['sessionToken'] = self.tok
        return h

    def sendRequest(self, method, body, header, httpMethod=None):
        """Wrap the call to URL open so that we can catch exceptions it might throw."""
        try:
            if(body):
                # Encode the string so it won't have database issues
                b = json2str(body)
            else:
                b = None
            req = urllib2.Request(self.baseUrl + method, b, header)
            if(httpMethod):
                req.get_method = lambda: httpMethod
            resp = urllib2.urlopen(req).read()
            
            # Decode any message returning that may have touched the database
            return str2json(resp)
        
        except urllib2.HTTPError as httpe:
            #Get the HTTP error data
            code = httpe.code
            msg = httpe.msg
            
            # Not ours, don't know what to do
            if(not pdapi.isPDError(code)):
                raise httpe
            
            # Check if sessionToken has expired, if so relogin
            if(code == pdapi.ERR_TOKEXPIRE):
                out.warn("** Please signin to API server again\n")
            else:
                out.err('!! %s PDAPIError %s: %s\n' % (logPrefix(), code, msg))
            return None
            
        except Exception as e:
            out.err('!! %s Unknown exception %s\n' % (logPrefix(), str(e)))
            return None
            
    def signin(self, uname=None, passwd=None):
        """Uses the signin API to get the sessionToken and devid of the developer."""
        if(uname and passwd):
            self.uname = uname
            self.passwd = md5.new(passwd).hexdigest()

        method = "auth/signin"
        headers = self.buildHeaders()
        
        # Send request
        resp = self.sendRequest(method, {'username': self.uname, 'password': self.passwd}, headers)
        if(not resp):
            return False
        
        # Verify response
        res = pdutils.check(resp, dict, ["sessionToken", "devid"])
        if(res):
            raise PDAPIError(method, "API server error signing in")
        
        # All good, set stuff
        self.devid = resp['devid']
        self.tok = resp['sessionToken']
        
        return True
    
    def signout(self):
        """Uses the signout API to destroy the sessionToken."""

        method = "auth/signout"
        headers = self.buildHeaders()
        
        # Send request
        resp = self.sendRequest(method, None, headers)
        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        if(res):
            return True
        else:
            return False

    def getApList(self):
        """Lists the APs associated with this developer."""
        method = "ap/list"
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return []
        
        # Verify response
        res = pdutils.check(resp, list)
        if(res):
            raise PDAPIError(method, "API server error getting AP list")
        
        #Convert the response into a list of AP() objects and return
        return [AP(descriptor=l) for l in resp]
    
    def setApInfo(self, ap):
        """Submits the info for the ap argument.
            Returns True in error."""
        method = "ap/%s/info" % ap.guid
        
        # Verify argument
        if(not isinstance(ap, AP)):
            raise PDAPIError(method, "AP object required")
        
        # Send request
        resp = self.sendRequest(method, ap.getAPIFormat(), self.buildHeaders())
        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        if(res):
            raise PDAPIError(method, "API server error setting AP info")
        
        # Check response back from server
        if(resp['response'] == 'OK'):
            return False
        else:
            return True

    def getApInfo(self, ap):
        """Gets the info for the ap argument."""
        # Object passed in can be an AP object or simply an ap guid string
        if (isinstance(ap, AP)):
            method = "ap/%s/info" % ap.guid
        else:
            # Most likely called by the pdcli program, so arg is a guid
            method = "ap/%s/info" % ap
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())

        # Verify response
        res = pdutils.check(resp, dict, None, valMatches={"response": 'OK'})
        if(res):
            raise PDAPIError(method, "API server error getting AP info")
        
        return resp['data']
    
    def getAPStatus(self, ap):
        """Get the status of this AP.
            Return dict object or None on error/missing."""
        if(isinstance(ap, AP)):
            apid = ap.guid
        else:
            apid = ap
        method = "ap/%s/status" % apid

        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return None

        # Verify response
        res = pdutils.check(resp, dict, response="OK", data=dict)
        if(res):
            return None
        else:
            return resp['data']
    
    def getAPUpdate(self, ap):
        """Get last update of this AP.
            Return dict of update data or None on error."""
        if(isinstance(ap, AP)):
            apid = ap.guid
        else:
            apid = ap
        
        method = "ap/%s/update" % apid
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return None

        # Verify response
        res = pdutils.check(resp, dict, response="OK", data=dict)
        if(res):
            return None
        else:
            return resp['data']
    
    def resetAP(self, ap):
        """Reset the AP.
            Return False in success, True in error."""
        if(isinstance(ap, AP)):
            apid = ap.guid
        else:
            apid = ap
        
        method = "ap/%s/reset" % apid
        
        # Send request
        resp = self.sendRequest(method, {"confirm": "yes"}, self.buildHeaders())
        if(not resp):
            return True

        # Verify response
        res = pdutils.check(resp, dict, response="OK")
        if(res):
            return True
        else:
            return False

    def listChutes(self, ap):
        """Get a list of the chutes for an AP.
            @returns chute objects or None on error."""
        
        # Object passed in can be an AP object or simply an ap guid string
        if (isinstance(ap, AP)):
            method = "ap/%s/list" % ap.guid
        else:
            # Most likely called by the pdcli program, so arg is a guid
            method = "ap/%s/list" % ap
            #raise PDAPIError(method, "AP object required")
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        
        # Verify response
        res = pdutils.check(resp, dict, ["data"], valMatches={"response": "OK"})
        if(res):
            raise PDAPIError(method, "API server error getting AP info")
       
        #Convert the response into a list of Chute() objects and return
        return [Chute(descriptor=l) for l in resp['data']]
    
    def createChute(self, ap):
        """Request a new chute for this AP.
            @returns a chute object or None on error."""
        
        # Object passed in can be an AP object or simply an ap guid string
        if (isinstance(ap, AP)):
            method = "ap/%s/newchute" % ap.guid
        else:
            # Most likely called by the pdcli program, so arg is a guid
            method = "ap/%s/newchute" % ap
            #raise PDAPIError(method, "AP object required")
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        
        # Verify response
        res = pdutils.check(resp, dict, ["data"], response= "OK")
        if(res):
            raise PDAPIError(method, "API server error getting AP info")
       
        # Return a Chute object
        return Chute(descriptor=resp['data'])
    
    def deleteChute(self, chute):
        """Request to delete a chute for this AP.
            @returns True on failure or False on success."""

        # Object passed in can be a Chute object or simply an chute guid string
        if (isinstance(chute, Chute)):
            method = "chute/%s/delete" % chute.guid
        else:
            # Most likely called by the pdcli program, so arg is a guid
            method = "chute/%s/delete" % chute
            #raise PDAPIError(method, "Chute object required")
        
        # Send request
        resp = self.sendRequest(method, {"confirm": "yes"}, self.buildHeaders())
        
        # Verify response
        res = pdutils.check(resp, dict, None, valMatches={"response": "OK"})
        if(res):
            return True
        
        # Return a false on success
        return False
    
    def getChuteInfo(self, chute):
        """Get the info for this chute.
            Return Chute object or None on failure."""
        
        # Object passed in can be a Chute object or simply an chute guid string
        if (isinstance(chute, Chute)):
            method = "chute/%s/info" % chute.guid
        else:
            # Most likely called by the pdcli program, so arg is a guid
            method = "chute/%s/info" % chute
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return None
        
        # Verify response
        res = pdutils.check(resp, dict, None, valMatches={'response':'OK'})
        if(res):
            raise PDAPIError(method, "API server error getting Chute info")
        
        # Return False meaning success
        return Chute(descriptor=resp['data'])

    def getChuteData(self, chute):
        """Get the data for this chute.
            All data will be returned including:
                - struct
                - runtime
                - traffic
                - resource
            Return Chute object or None on failure."""
        
        # Object passed in can be a Chute object or simply an chute guid string
        if (isinstance(chute, Chute)):
            method = "chute/%s/data" % chute.guid
        else:
            # Most likely called by the pdcli program, so arg is a guid
            method = "chute/%s/data" % chute
        
        # Send request
        # TODO- change to handle chute objects
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return None
        
        # Verify response
        res = pdutils.check(resp, dict, None, valMatches={'response':'OK'})
        if(res):
            raise PDAPIError(method, "API server error getting Chute info")
        
        # Return False meaning success
        return Chute(descriptor=resp['data'])
    
    def setChuteData(self, chute):
        """Set the data for this chute.
            All data will be sent:
                - struct
                - runtime
                - traffic
                - resource
                - files
            Return True in error."""
        
        # Verify argument
        if(not isinstance(chute, Chute)):
            raise PDAPIError(method, "Chute object required")
        
        method = "chute/%s/data" % chute.guid
        
        # Send request
        resp = self.sendRequest(method, chute.getAPIDataFormat(), self.buildHeaders())
        
        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        if(res):
            return True
        
        # Return False meaning success
        return False

    def setChuteInfo(self, chute):
        """Set the info for this chute.
            Return True on failure or False on success."""
        # Verify argument
        if(not isinstance(chute, Chute)):
            raise PDAPIError(method, "Chute object required")
        
        method = "chute/%s/info" % chute.guid
            
        # Send request
        resp = self.sendRequest(method, chute.getAPIFormat(), self.buildHeaders())
        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        
        # Return False meaning success
        if(res):
            return True
        else:
            return False

    def enableChute(self, ch):
        """Enable the chute."""
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        
        method = "chute/%s/enable" % chid

        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        if(res):
            return True
        else:
            return False

    def disableChute(self, ch):
        """Disable the chute."""
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        method = "chute/%s/disable" % chid
        
        # Verify argument
        if(not isinstance(ch, Chute)):
            raise PDAPIError(method, "Chute object required")
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        if(res):
            return True
        else:
            return False

    def freezeChute(self, ch):
        """Freeze the chute."""
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        method = "chute/%s/freeze" % chid
        
        # Verify argument
        if(not isinstance(ch, Chute)):
            raise PDAPIError(method, "Chute object required")
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        if(res):
            return True
        else:
            return False

    def unfreezeChute(self, ch):
        """Unfreeze the chute."""
        # Verify argument
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        method = "chute/%s/unfreeze" % chid
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        if(res):
            return True
        else:
            return False
    
    def getChuteStatus(self, ch):
        """Get the status of this chute.
            Return dict of status data or None on error."""
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        
        method = "chute/%s/status" % chid
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return None

        # Verify response
        res = pdutils.check(resp, dict, response="OK", data=dict)
        if(res):
            return None
        else:
            return resp['data']
    
    def getChuteUpdate(self, ch):
        """Get last update of this chute.
            Return dict of update data or None on error."""
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        
        method = "chute/%s/update" % chid
        
        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders())
        if(not resp):
            return None

        # Verify response
        res = pdutils.check(resp, dict, response="OK", data=dict)
        if(res):
            return None
        else:
            return resp['data']
    
    def putChuteFile(self, ch, filePath):
        """Transmit a file to the server"""
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        
        if os.path.isdir(filePath):
            dir_resp = "Is a Directory. PutFile works only for files. Please Re-try"
            return dir_resp

        hundredMB = (100 * 1024 * 1024)
        if os.path.getsize(filePath) > hundredMB:
            size_resp = "File size exceeded max limit (100MB). Please Re-try"
            return size_resp

        fileObj = open(filePath, 'rb')
        reqSize = os.stat(filePath).st_size 
        fileName = filePath.split('/')[-1]
        method = "chute/%s/file/%s" % (chid, fileName)
        mmapFileObj = mmap.mmap(fileObj.fileno(), 0, access=mmap.ACCESS_READ)

        # Send request
        encFileObj = base64.b64encode(mmapFileObj.read(mmapFileObj.size()))
        resp = self.sendRequest(method, encFileObj, self.buildHeaders(fileName, reqSize), httpMethod='PUT')

        mmapFileObj.close()
        fileObj.close()

        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        if(res):
            return True
        else:
            return resp 

    def deleteChuteFile(self, ch, fileName):
        """Delete a file from the server"""
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        method = "chute/%s/file/%s" % (chid, fileName)


        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders(fileName), httpMethod='DELETE')
        if(not resp):
            return True

        # Verify response
        res = pdutils.check(resp, dict, ["response"])
        if(res):
            return True #Failed checks
        else:
            return resp #Passed checks

    def getStatsChuteFile(self, ch, fileName):
        """Gets Stat of a file from the server"""
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        method = "chute/%s/file/%s" % (chid, fileName)


        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders(fileName), httpMethod='GET')
        if(not resp):
            return True
        
        # Verify response
        res = pdutils.check(resp, dict)
        if(res):
            return True 
        else:
            return resp

    def listChuteFiles(self, ch):
        """Get list of chute files from the server"""
        if(isinstance(ch, Chute)):
            chid = ch.guid
        else:
            chid = ch
        
        method = "chute/%s/files" % chid

        # Send request
        resp = self.sendRequest(method, None, self.buildHeaders(), httpMethod='GET')
        if(not resp):
            return True

        res = pdutils.check(resp, list)
        if(res):
            return True 
        else:
            return resp



