###################################################################
# Copyright 2013-2014 All Rights Reserved
# Authors: The Paradrop Team
###################################################################

import math, time, uuid, random

from lib.paradrop import *
from lib.paradrop.pderror import PDError
portion = lambda x: x[0:int(math.ceil(len(x)*0.25))]

def generateToken(sz=128):
    return str(hex(random.getrandbits(sz)))

def getNewGuid(name=None):
    """This uses the UUID module to return a new random GUID string.
        If you provide a name, it will return a UUID based on the NAMESPACE_DNS associated
        to the name you provided.
        NOTE: What this means is if you provide 'test' as the name the GUID will ALWAYS BE THE SAME!
              IT WAS DESIGNED THIS WAY FOR UNIT TESTING PURPOSES AND SHOULD NOT BE USED IN PRODUCTION."""
    if(name):
        return str(uuid.uuid3(uuid.NAMESPACE_DNS, name))
    else:
        return str(uuid.uuid4())
        

def isGuid(g):
    """Checks input for a valid GUID.
        Returns True if is a GUID, False otherwise."""
    
    # Make sure we can read it
    if(type(g) is not str):
        return False
    
    # Check length
    if(len(g) != 36):
        return False

    # Check format, should be a set of digits of lengths in the compareTo array separated by '-'s
    compareTo = [8, 4, 4, 4, 12]
    return compareTo == [len(i) for i in g.split('-')]

def hashJson(j):
    """Returns a string hash of a JSON object."""
    try:
        return str(hex(abs(hash(frozenset(j)))))
    except Exception as e:
        s = str(j)
        out.err('!! Error hashing %s\n' % portion(s))
        out.err('!! Exception: %s\n' % str(e))
        return ""

def isValidStateTransition(curState, nextState):
    """Returns True if the transition is OK, otherwise returns False."""
    # Any invalid is bad
    if(curState == 'invalid' or nextState == 'invalid'):
        return False

    # If currently running, any other state is ok (not itself)
    if(curState == 'running' and nextState != "running"):
        return True

    # If currently stopped, can only go to running or disabled
    if(curState == 'stopped'):
        return (nextState == 'running' or nextState == 'disabled')

    # If currently frozen, only can go to enabled
    if(curState == "frozen"):
        return (nextState == 'running')
    
    # If currently disabled, can only enable
    if(curState == "disabled"):
        return nextState == "running"

    # Anything else is bad
    return False


def check(pkt, pktType, keyMatches=None, **valMatches):
    """This function takes an object that was expected to come from a packet (after it has been JSONized)
        and compares it against the arg requirements so you don't have to have 10 if() statements to look for keys in a dict, etc..
        
        Args:
            @pkt             : object to look at
            @pktType         : object type expected (dict, list, etc..)
            @keyMatches      : a list of minimum keys found in parent level of dict, expected to be an array
            @valMatches      : a dict of key:value pairs expected to be found in the parent level of dict
                              the value can be data (like 5) OR a type (like this value must be a @list@).
        Returns:
            None if everything matches, otherwise it returns a string as to why it failed."""
    #First check that the pkt type is equal to the input type
    if(type(pkt) is not pktType):
        return 'expected %s' % str(pktType)
    
    if(keyMatches):
        # Convert the keys to a set
        keyMatches = set(keyMatches)
        #The keyMatches is expected to be an array of the minimum keys we want to see in the pkt if the type is dict
        if(type(pkt) is dict):
            if(not keyMatches.issubset(pkt.keys())):
                return 'missing, "%s"' % ', '.join(list(keyMatches - set(pkt.keys())))
        else:
            return None

    #Finally for anything in the valMatches find those values
    if(valMatches):
        # Pull out the dict object from the "valMatches" key
        if('valMatches' in valMatches.keys()):
            matchObj = valMatches['valMatches']
        else:
            matchObj = valMatches
            
        for k, v in matchObj.iteritems():
            #Check for the key
            if(k not in pkt.keys()):
                return 'key missing "%s"' % k
            
            #See how we should be comparing it:
            if(type(v) is type):
                if(type(pkt[k]) is not v):
                    return 'key "%s", bad value type, "%s", expected "%s"' % (k, type(pkt[k]), v)
            
            else:
                #If key exists check value
                if(v != pkt[k]):
                    return 'key "%s", bad value data, "%s", expected "%s"' % (k, pkt[k], v)
    
    return None
        
def explode(pkt, *args):
    """This function takes a dict object and explodes it into the tuple requested.
    
        It returns None for any value it doesn't find.

        The only error it throws is if args is not defined.
        
        Example:
            pkt = {'a':0, 'b':1}
            0, 1, None = pdcomm.explode(pkt, 'a', 'b', 'c')
    """
    if(not args):
        raise PDError('EXPLODE', 'args must be provided')
    
    # If there is an error make sure to return a tuple of the proper length
    if(not isinstance(pkt, dict)):
        return tuple([None] * len(args))
    
    # Now just step through the args and pop off everything from the packet
    # If a key is missing, the pkt.get(a, None) returns None rather than raising an Exception
    return tuple([pkt.get(a, None) for a in args])
