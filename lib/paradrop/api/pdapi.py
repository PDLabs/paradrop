import random, math

from lib.paradrop import *

class PDAPIError(Exception):
    """
        Exception class related to ParaDrop API calls.
    """
    def __init__(self, etype, msg):
        self.etype = etype
        self.msg = msg
    
    def __str__(self):
        return "PDAPIError %s: %s" % (self.etype, self.msg)


def isPDError(code):
    """Checks all Paradrop API error codes, if the HTTP code is in our set it is assumed a PDAPI error."""
    if(code in RESP_MSG.keys()):
        return True
    else:
        return False

DEFAULT_API_KEYS = {
    "ap/list": ['name', 'guid', 'contact'],
}

OK = 200
ERR_BADPARAM = 400
ERR_TOKEXPIRE = 401
ERR_BADFORMAT = 402
ERR_BADAUTH = 403
ERR_BADMETHOD = 405
ERR_BADIO=406
ERR_BADPATH=407
ERR_CONTACTPD = 501
ERR_DBISSUE = 502
ERR_STATECHANGE = 503
ERR_CHUTESTATE = 504
ERR_UPDATEPENDING = 505
ERR_NOSTATUS = 506
ERR_RESETPENDING = 507
ERR_CHUTEINVALID = 508
ERR_UNIMPLEMENTED = 599

RESP_MSG = {
  OK: None,
  ERR_BADPARAM: "Bad parameter: %s",
  ERR_TOKEXPIRE: "Token expired",
  ERR_BADFORMAT: "Bad format",
  ERR_BADAUTH: "Bad authorization",
  ERR_BADMETHOD: "Bad method type",
  ERR_BADIO: "Bad IO",
  ERR_BADPATH: "Path not found",
  ERR_CONTACTPD: "Contact Paradrop, ERRORTOKEN: %s",
  ERR_DBISSUE: "Issue with database, please try again",
  ERR_STATECHANGE: "Bad state transition",
  ERR_CHUTESTATE: "Cannot make change with chute in its current state",
  ERR_UPDATEPENDING: "Action already pending for Chute",
  ERR_NOSTATUS: "No status data available, either none exists or bad authorization",
  ERR_RESETPENDING: "Reset already pending for AP",
  ERR_CHUTEINVALID: "Cannot make change, chute would become invalid",
  ERR_UNIMPLEMENTED: "Function unimplemented yet",
}


def getResponse(code, *args):
    """Designed to be called to provide the arguments for the Request.setResponseCode()"""
    if(len(args) == 0):
        return code, RESP_MSG[code]
    else:
        return code, RESP_MSG[code] % (args)

def getErrorToken():
    """Generates a random string which is used to match client issues with log output."""
    return '%010d' % int(random.getrandbits(32))

def getAPIKeys(method):
    """Returns the default key set related to the @method argument."""
    if(method in DEFAULT_API_KEYS.keys()):
        return DEFAULT_API_KEYS[method]
    else:
        raise PDAPIError('GetAPIKeys', 'Invalid method')

