###################################################################
# Copyright 2013-2014 All Rights Reserved
# Authors: The Paradrop Team
###################################################################

import sys, argparse, re, traceback, collections, os, pickle
from lib.paradrop import *
from lib.paradrop import chute
from lib.paradrop import ap
from lib.paradrop.api import client

def setupArgParse():
    p = argparse.ArgumentParser(description='Daemon for the ParaDrop Framework Control program which runs on routers')
    p.add_argument('-a', '--addr', help='Address to connect to', type=str, default='paradrop.org')
    p.add_argument('-p', '--port', help='Port to connect to', type=int, default=10000)
    p.add_argument('-g', '--guid', help='Developer GUID', type=str)
    return p

def breakdown(a):
    """Used by the get/set commands to help deal with when the user uses a '@' in a function."""
    regex = re.compile('@([a-zA-Z]*)')
    mat = regex.match(a)
    if(mat):
        var, = mat.groups(1)
        return (var, a.replace('@%s' % var, ''))
    return (a, a)

class PDCLI(object):
    """@decorator helper
        This class is used to register helper functions to implement the CLI program.
        It should be called like:
            
            # Need to get a handle to the CLI
            pdcli = PDCLI()
            
            # All commands will exist in this class
            class Commands()
                def __init__(self):
                    # Need to get a reference to the pdcli for runtime stuff
                    self.cmd = pdcli
                    # Need to tell pdcli who the command class is
                    pdcli.cli = self
                # Decorate the help function by specifying the regex
                @pdcli.register('^help$')
                def help(self, line):
                    print('stuff')

        Exposed functions:
            printHelps : prints all help data
            findMatch  : Calls the function match for the regex provided
    """
    def __init__(self, *args):
        self.regexes = []
        self.funcs = []
        self.helps = []
        self.auths = []
        self.cmd = None
        self.allFunc = None
        self.loggedIn = False
    
    def printHelps(self, tok=None):
        # Figure out how large the __name__ should be
        if(tok):
            tok = tok.lstrip()
        fs = []
        hs = []
        m = None
        # Look through all registered functions
        for f, h in zip(self.funcs, self.helps):
            if(h):
                # See if we should be filtering
                if(tok and tok not in f.__name__):
                    continue
                    
                l = len(f.__name__)
                if(not m or l > m):
                    m = l
                fs.append(f.__name__)
                hs.append(h)
        if(not m):
            self.cmd.outfd('No functions match that input\n')
            return
        s = "%%%ds : %%s" % (m + 1)
        for f, h in zip(fs, hs):
            self.cmd.outfd(s % (f, h))

    def findMatch(self, line):
        # Check for help thing
        if('-?' in line or '-h' in line):
            line = line.strip('-?').strip('-h').rstrip()
            for r, f, h, a in zip(self.regexes, self.funcs, self.helps, self.auths):
                if(line == f.__name__):
                    return self.cmd.outfd(h)
            else:
                return self.allFunc(self.cmd)
                    
        else:
            for r, f, h, a in zip(self.regexes, self.funcs, self.helps, self.auths):
                m = r.match(line)
                if(m):
                    if(a and self.loggedIn):
                        return f(self.cmd, *m.groups())
                    elif(a and not self.loggedIn):
                        return self.cmd.outfd('Must be logged in to use this function\n')
                    else:
                        return f(self.cmd, *m.groups())
        
            else:
                # No match so throw catchall
                return self.allFunc(self.cmd)

    def register(self, regex, auth=False, help=""):
        """@decorator
            This function is used to decorate other functions which represent
            individual commands as part of the CLI.
        """
        self.regexes.append(re.compile(regex))
        self.helps.append(help)
        self.auths.append(auth)

        def _decorator(func):
            self.funcs.append(func)
            return func
        
        return _decorator

    def catchall(self, func):
        """@decorator
            This function should be used to define what to call if there is no match.
        """
        self.allFunc = func
        return func


pdcli = PDCLI()

class PDCommands:
    """
        The Paradrop Command Line Interface class.

        This handles all the CLI commands the user might run.
    """
    def __init__(self, infd, outfd, clt, prompt='pd> '):
        self.infd = infd
        self.outfd = outfd
        self.prompt = prompt
        self.clt = clt
        self.cli = pdcli
        self.var = {}
        self.log = collections.deque([], 20)
        pdcli.cmd = self
        self.loggedIn = False
        # These are the active objects which are manipulated to set new data
        # If a new chute is created, it is automatically loaded into the active chute
        # Otherwise, loaded from the list of aps/chutes in self.var
         
    def clearLineAndReprompt(self):
        self.outfd('\x1b[2K\x1b[1G%s' % self.prompt)
    
    def readline(self, echo=True):
        """Read a line from outfd."""
        import termios, tty
        fd = self.infd.fileno()
        old = termios.tcgetattr(fd)
        
        try:
            tty.setraw(fd)
            line = ""
            ctrl = None
            ptr = 0
            while(True):
                # Read in chars, 1 at a time
                l = self.infd.read(1)
                # If they hit enter
                if(l == '\r'):
                    self.outfd('\r\n')
                    break
                # If they hit Ctrl-C
                elif(l == '\x03'):
                    self.outfd('Use ^D to exit\r\n')
                    line = ""
                    break
                # If they hit Ctrl-D
                elif(l == '\x04'):
                    self.outfd('\r\n')
                    exit()
                # If they hit backspace
                elif(l == '\x7f'):
                    # Delete from the line, but if line is empty don't do anything
                    if(len(line) > 0):
                        line = line[:-1]
                        # Move the cursor back 1 space then delete the char
                        self.outfd('\x1b[1D\x1b[0K')
                    continue

                # If a control sequence is pressed (up/down/left/right arrow)
                elif(l == '\x1b'):
                    ctrl = l
                    continue
                # If a ctrl was pressed, there should be 3 keys
                # TODO - shouldn't be able to move around left/right
                if(ctrl):
                    ctrl += l
                    if(len(ctrl) == 3):
                        if(ctrl == '\x1b[A'): #Pressed up??
                            self.clearLineAndReprompt()
                            ptr -= 1
                            try:
                                line = self.log[ptr]
                            except:
                                ptr += 1
                            self.outfd(line)
                        elif(ctrl =='\x1b[B'): #Pressed down??
                            self.clearLineAndReprompt()
                            ptr += 1
                            try:
                                line = self.log[ptr]
                            except:
                                ptr -= 1
                            self.outfd(line)
                        elif(ctrl =='\x1b[C'): #Pressed right?
                            self.outfd("\x1b[1C")
                        elif(ctrl =='\x1b[D'): #Pressed left
                            self.outfd("\x1b[1D")
                        ctrl = None
                    continue
                
                if(echo):
                    self.outfd(l)
                line += l

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        
        return line

    def run(self):
        """
            Main running function, loops through forever until the user kills us.
        """
        # Let the user know what to do
        self.catchall()
        
        while(True):
            try:
                self.outfd(self.prompt)
                line = self.readline()
                self.log.append(line)
                self.cli.findMatch(line)

            except Exception as e:
                out.err('!! Error: %s\n%s\n' % (str(e), traceback.format_exc()))

    @pdcli.register('^help(.*)')
    def help(self, tok=None):
        self.cli.printHelps(tok)
    
    @pdcli.register('^clear$')
    def clear(self):
        # Clear the screen, move the cursor to top left
        self.outfd('\x1b[2J\x1b[1;1H')
    
    @pdcli.register('^quit|exit')
    def quit(self):
        sys.exit()
    
    @pdcli.register('^set (.*)=(.*)', help="Set <name>=<value> - holds onto the value in this variable, used for different functions\n")
    def set(self, name, value):
        # Deal with name containing a '@'
        if('@' in name):
            var1, var2 = breakdown(name)
            name = 'self.var["%s"]%s' % (var1, var2)
        else:
            name = 'self.var["%s"]' % name
        
        # Deal with value containing '@'
        if('@' in value):
            var1, var2 = breakdown(value)
            value = 'self.var["%s"]%s' % (var1, var2)

        # Since we are setting something we have to use 'exec'
        try:
            exec('%s = %s' % (name, value))
        except Exception as e:
            self.outfd('Error: %s\n' % str(e))
    
    @pdcli.register('^get (.*)', help="Get <name|*> - Print what the variable is, or all if '*'\n")
    def get(self, name):
            
        if(name == '*'):
            for k,v in self.var.iteritems():
                self.outfd('%s = %r\n' % (k, v))
        
        elif('@' in name):
            var1, var2 = breakdown(name)
            s = "self.var['%s']%s" % (var1, var2)
            self.outfd('%s\n' % eval(s))
            
        else:
            if(name in self.var):
                self.outfd('%s = %s\n' % (name, self.var[name]))
            else:
                self.outfd('%s not defined\n' % name)
    
    @pdcli.register('^delete (.*)', help="Delete <name> - Delete the variable specified\n")
    def delete(self, name):
        if(name in self.var):
            del(self.var[name])
            self.outfd('Removed %r\n' % name)
        else:
            self.outfd('%r not defined\n' % name)
    
    @pdcli.register('^save', help="Save the environment state to PDPATH/.pdcli\n")
    def save(self):
        if('PDPATH' in os.environ):
            path = "%s/.pdcli" % os.environ['PDPATH']
        else:
            self.outfd("PDPATH not defined, saving to './.pdcli' instead\n")
            path = "./.pdcli"
        try:
            fd = open(path, 'wb')
            pickle.dump(self.var, fd)
            fd.close()
        except Exception as e:
            self.outfd('Unable to save: %s\n' % str(e))
    
    @pdcli.register('^load', help="Load the environment state from PDPATH/.pdcli\n")
    def load(self):
        if('PDPATH' in os.environ):
            path = "%s/.pdcli" % os.environ['PDPATH']
        else:
            self.outfd("PDPATH not defined, attempting load from './.pdcli' instead\n")
            path = "./.pdcli"
        try:
            fd = open(path, 'rb')
            self.var = pickle.load(fd)
            fd.close()
        except Exception as e:
            self.outfd('Unable to load: %s\n' % str(e))
    
    @pdcli.register('^login (.*)', help="login <username>\n")
    def login(self, uname):
        uname = uname.lstrip()
        self.outfd('Password: ')
        pw = self.readline(echo=False)
        if(self.clt.signin(uname, pw)):
            self.cli.loggedIn = True
            self.prompt = uname + '@pd> ' 
    
    @pdcli.register('^logout$', help="logout\n")
    def logout(self):
        self.cli.loggedIn = False 
        self.prompt = 'pd> '
        self.clt.signout()
    
    @pdcli.register('^apList', True, help="Get the list of APs associated to dev id, stored to variable: aps\n")
    def apList(self):
        aps = self.clt.getApList()
        self.var['aps'] = aps
        self.outfd("Setting 'aps' to the list below:\n")
        for i, a in enumerate(aps):
            self.outfd("[%3d] : %r\n" % (i, a))
   
    @pdcli.register('^apGetInfo(.*)', True, help="Get the info for this AP\n")
    def apGetInfo(self, ap=None):
        # First check if command line argument is given, otherwise check apid var
        if(ap):
            apInfo = self.clt.getApInfo(ap)
        elif('activeAP' in self.var):
            apInfo = self.clt.getApInfo(self.var['activeAP'])
        else:
            self.outfd('No AP provided, define using "set activeAP" or provide AP object as argument\n')
            return

        self.outfd("%s\n" % apInfo)
    
    @pdcli.register('^apSetInfo(.*)', True, help="Set the info for this AP\n")
    def apSetInfo(self, ap=None):
        # First check if command line argument is given, otherwise check apid var
        if(ap):
            a = ap
        elif('activeAP' in self.var):
            a = self.var['activeAP']
        else:
            self.outfd('No AP provided, define using "set activeAP" or provide AP object as argument\n')
            return
        if(self.clt.setApInfo(a)):
            self.outfd('Error setting AP Info\n')
        else:
            self.outfd('Success\n')
    
    @pdcli.register('^apGetStatus', True, help="Get status details of the AP\n")
    def apGetStatus(self):
        if('activeAP' in self.var):
            retVal = self.clt.getAPStatus(self.var['activeAP'])
            if(retVal):
                self.outfd('%s\n' % retVal)
            else:
                self.outfd('Error getting status\n')
        else:
            self.outfd('"set activeAP" before calling this function\n')
            return
    
    @pdcli.register('^apGetUpdate', True, help="Get last update of the AP\n")
    def apGetUpdate(self):
        if('activeAP' in self.var):
            retVal = self.clt.getAPUpdate(self.var['activeAP'])
            if(retVal):
                self.outfd('%s\n' % retVal)
            else:
                self.outfd('No updates available\n')
        else:
            self.outfd('No AP provided, define using "set activeAP"\n')
            return
    
    @pdcli.register('^apReset(.*)', True, help="Fully reset the AP back to defaults\n")
    def apReset(self, ans=None):
        if('activeAP' in self.var):
            if(ans and ans.lstrip() == 'confirm'):
                if(self.clt.resetAP(self.var['activeAP'])):
                    self.outfd('Failed to reset\n')
                else:
                    self.outfd('Reset now pending\n')
            else:
                self.outfd('This FULLY resets the AP to a default state including all configuration files and deleting ALL chutes and Chute data.\nPlease enter "confirm" as an argument to this call.\n')
        else:
            self.outfd('No AP provided, define using "set activeAP"\n')

    @pdcli.register('^chuteList', True, help="List all current chutes for the AP\n")
    def chuteList(self):
        if('activeAP' in self.var):
            chutes = self.clt.listChutes(self.var['activeAP'])
        else:
            self.outfd('No AP provided, define using "set activeAP"\n')
            return

        self.var['chutes'] = chutes
        
        self.outfd("Setting 'chutes' to the list below:\n")
        for i,c in enumerate(chutes):
            self.outfd("[%2d] : %r\n" % (i, c))
    
    @pdcli.register('^chuteCreate', True, help="Get a new Chute for the 'activeAP'\n")
    def chuteCreate(self):
        if('activeAP' in self.var):
            # This is either successful or raises an Exception so no need to check return
            newch = self.clt.createChute(self.var['activeAP'])
        else:
            self.outfd('No AP provided, define using "set activeAP"\n')
            return
       
        
        if('activeChute' in self.var):
            self.var['newChute'] = newch
            self.outfd('Setting new chute to "newChute"\n')
        else:
            self.outfd('Setting new chute to "activeChute"\n')
            self.var['activeChute'] = newch
     
    @pdcli.register('^chuteDelete(.*)', True, help="Delete a current chute from the AP\n")
    def chuteDelete(self, ch=None):
        if(ch):
            pass
        elif('activeChute' in self.var):
            ch = self.var['activeChute']
        else:
            self.outfd('No Chute provided, define using "set activeChute" or provide Chute object as argument\n')
            return

        if(self.clt.deleteChute(ch)):
            self.outfd('Error deleting chute\n')
        else:
            # Remove chute from vars
            if('chutes' in self.var):
                todel = None
                for i, c in enumerate(self.var['chutes']):
                    if(c.guid == ch.guid):
                        todel = i
                        break
                if(todel):
                    del(self.var['chutes'][i])
                
            self.outfd('chute delete pending, check with chuteGetUpdate\n')
    
    @pdcli.register('^chuteGetInfo(.*)', True, help="Get the info for this Chute\n")
    def chuteGetInfo(self, ch=None):
        # First check if command line argument is given, otherwise check chuteid var
        if(ch):
            chuteInfo = self.clt.getChuteInfo(ch)
            self.outfd("%s\n" % chuteInfo)
        elif('activeChute' in self.var):
            chuteInfo = self.clt.getChuteInfo(self.var['activeChute'])
            self.var['activeChute'].merge(chuteInfo, avoid=['internalid'])
            self.outfd("%s\n" % self.var['activeChute'])
        else:
            self.outfd('No Chute provided, define using "set activeChute" or provide Chute object as argument\n')
            return
    
    @pdcli.register('^chuteGetData', True, help="Get the data for this Chute\n")
    def chuteGetData(self, varName='activeChute'):
        # First check if command line argument is given, otherwise check chuteid var
        if(varName in self.var):
            chuteInfo = self.clt.getChuteData(self.var[varName])
        else:
            self.outfd('No Chute provided, define using "set activeChute" or provide Chute object as argument\n')
            return
        self.outfd('Setting "%s" to this data\n' % varName)
        self.var[varName] = chuteInfo
        self.outfd("%s\n" % chuteInfo)
   
    @pdcli.register('^chuteLoad(.*)', help="Loads chute from file, uses extension type of '*.chute' to load manifest file, and '*.py' to load from Python file\n")
    def chuteLoad(self, args):
        args = args.lstrip().split(' ')
        if(len(args) == 3):
            chp, chn, chc = args
        elif(len(args) == 2):
            chp, chn = args
            chc = None
        else:
            out.err('Usage: chuteLoad <path> <chuteName> [category]\n')
            return
        
        # Are we loading from manifest or Python?
        if('.chute' in chp):
            # See if there is a chute defined with the name they gave
            ch = self.var.get(chn, chute.Chute())
            ch = chute.loadManifest(chp, ch, chc)
            if(ch):
                self.var[chn] = ch
                self.outfd('%s: %s\n' % (chn, ch))
            else:
                out.err('Unable to get manifest\n')
        elif('.py' in chp):
            try:
                modname = chp.strip('.py').replace('/', '.')
                if(modname.startswith('.')):
                    modname = modname[1:]
                themod = __import__(modname, fromlist=[modname])
                # Now reload the module so we get a fresh copy
                themod = reload(themod)
                # make sure they defined loadme
                if('loadme' in themod.__dict__):
                    # Now find the loadme variable which contains what we want to use and load it
                    if(chn not in self.var):
                        self.var[chn] = chute.Chute()
                    self.var[chn].merge(themod.__dict__[themod.loadme], avoid=['guid', 'apid', 'internalid', 'devinfo', 'state', 'contact'])
                    self.outfd('%s: %s\n' % (chn, self.var[chn]))
                else:
                    self.outfd('Malformed Python module, you must define the "loadme" variable to be the chute variable name you want me to load!\n')
            except Exception as e:
                self.outfd('Unable to load chute: %s\n' % str(e))
        else:
            self.outfd('Unable to determine extension type, supported: chute, py\n')
    
    @pdcli.register('^chuteSave(.*)', help="Stores the chute definition to a local manifest file\n")
    def chuteSave(self, chPath=None):
        if(not chPath):
            self.outfd('No path specified, please provide the path\n')
            return
        else:
            if('activeChute' not in self.var):
                self.outfd('No Chute provided, define using "set activeChute"\n')
                return
                
            chPath = chPath.lstrip()
            if(chute.storeManifest(self.var['activeChute'], chPath)):
                self.outfd('Error saving chute\n')
            else:
                self.outfd('Saved\n')
    
    @pdcli.register('^chuteSetData', True, help="Set the data in database for some active chute\n")
    def chuteSetData(self):
        # First check if command line argument is given, otherwise check chuteid var
        if('activeChute' in self.var):
            if(self.clt.setChuteData(self.var['activeChute'])):
                self.outfd('Error setting chute data\n')
            else:
                self.outfd('Chute data set now pending\n')
        else:
            self.outfd('No Chute provided, define using "set activeChute" or provide Chute object as argument\n')
            return
            
    @pdcli.register('^chuteSetInfo', True, help="Set the info in database for this Chute\n")
    def chuteSetInfo(self):
        if('activeChute' in self.var):
            if(self.clt.setChuteInfo(self.var['activeChute'])):
                self.outfd('Error setting chute info\n')
            else:
                self.outfd('Chute info successfully set\n')
        else:
            self.outfd('No Chute provided, define using "set activeChute" or provide Chute object as argument\n')
            return

    @pdcli.register('^chuteEnable(.*)', True, help="Start the actual chute\n")
    def chuteEnable(self, ch=None):
        # First check if command line argument is given, otherwise check chuteid var
        if(ch):
            retVal = self.clt.enableChute(ch)
        elif('activeChute' in self.var):
            retVal = self.clt.enableChute(self.var['activeChute'])
        else:
            self.outfd('No Chute provided, define using "set activeChute" or provide Chute object as argument\n')
            return
        # Handle retval (should be false)
        if(retVal):
            self.outfd('Error enabling chute\n')
        else:
            self.outfd('Chute enable now pending\n')
    
    @pdcli.register('^chuteDisable(.*)', True, help="Stop the actual chute\n")
    def chuteDisable(self, ch=None):
        # First check if command line argument is given, otherwise check chuteid var
        if(ch):
            retVal = self.clt.disableChute(ch)
        elif('activeChute' in self.var):
            retVal = self.clt.disableChute(self.var['activeChute'])
        else:
            self.outfd('No Chute provided, define using "set activeChute" or provide Chute object as argument\n')
            return
        # Handle retval (should be false)
        if(retVal):
            self.outfd('Error disabling chute\n')
        else:
            self.outfd('Chute disable now pending\n')

    @pdcli.register('^chuteFreeze(.*)', True, help="Freeze the chute in its current state\n")
    def chuteFreeze(self, ch=None):
        # First check if command line argument is given, otherwise check chuteid var
        if(ch):
            retVal = self.clt.freezeChute(ch)
        elif('activeChute' in self.var):
            retVal = self.clt.freezeChute(self.var['activeChute'])
        else:
            self.outfd('No Chute provided, define using "set activeChute" or provide Chute object as argument\n')
            return
        # Handle retval (should be false)
        if(retVal):
            self.outfd('Error freezing chute\n')
        else:
            self.outfd('Chute freeze now pending\n')

    @pdcli.register('^chuteUnfreeze(.*)', True, help="Unfreeze the chute, start running\n")
    def chuteUnfreeze(self, ch=None):
        # First check if command line argument is given, otherwise check chuteid var
        if(ch):
            retVal = self.clt.unfreezeChute(ch)
        elif('activeChute' in self.var):
            retVal = self.clt.unfreezeChute(self.var['activeChute'])
        else:
            self.outfd('No Chute provided, define using "set activeChute" or provide Chute object as argument\n')
            return
        # Handle retval (should be false)
        if(retVal):
            self.outfd('Error unfreezing chute\n')
        else:
            self.outfd('Chute unfreeze now pending\n')
    
    @pdcli.register('^chuteGetStatus', True, help="Get status details of the chute\n")
    def chuteGetStatus(self):
        if('activeChute' in self.var):
            retVal = self.clt.getChuteStatus(self.var['activeChute'])
            if(retVal):
                self.outfd('%s\n' % retVal)
            else:
                self.outfd('No status available\n')
        else:
            self.outfd('No Chute provided, define using "set activeChute"\n')
            return
    
    @pdcli.register('^chuteGetUpdate', True, help="Get last update of the chute\n")
    def chuteGetUpdate(self):
        if('activeChute' in self.var):
            retVal = self.clt.getChuteUpdate(self.var['activeChute'])
            if(retVal):
                self.outfd('%s\n' % retVal)
            else:
                self.outfd('No updates available\n')
        else:
            self.outfd('No Chute provided, define using "set activeChute"\n')
    
    @pdcli.register('^sendFile (.*)', True, help="Transmit a file to the API server\n")
    def sendFile(self, name):
        if('activeChute' in self.var):
            retVal = self.clt.putChuteFile(self.var['activeChute'], name)
            if(retVal == True):
                self.outfd('Unable to send file\n')
            else:
                self.outfd('Put file status for "%s" : %s\n' %(name, retVal))
        else:
            self.outfd('No Chute provided, define using "set activeChute"\n')

    @pdcli.register('^delFile (.*)', True, help="Delete a file from the API server\n")
    def delFile(self, name):
        if('activeChute' in self.var):
            retVal = self.clt.deleteChuteFile(self.var['activeChute'], name)
            if(retVal == True):
                self.outfd('Unable to delete file\n')
            else:
                self.outfd('File Deletion Status for "%s" : %s \n' %(name, retVal))
        else:
            self.outfd('No Chute provided, define using "set activeChute"\n')

    @pdcli.register('^statFile (.*)', True, help="Get file stats for a given file from the API server\n")
    def statFile(self, name):
        if('activeChute' in self.var):
            retVal = self.clt.getStatsChuteFile(self.var['activeChute'], name)
            if(retVal == True):
                self.outfd('Unable to get filestats\n')
            else:
                self.outfd('File Stats for "%s":\n%s\n' % (name, retVal))
        else:
            self.outfd('No Chute provided, define using "set activeChute"\n')

    
    @pdcli.register('^listFile', True, help="List files for a given chute from the API server\n")
    def listFile(self):
        if('activeChute' in self.var):
            retVal = self.clt.listChuteFiles(self.var['activeChute'])
            if(retVal == True):
                self.outfd('Unable to list files for Chute "%s"\n' %(self.var['activeChute']))
            else:
                self.outfd('Files in Chute:\n%s\n' % retVal)
        else:
            self.outfd('No Chute provided, define using "set activeChute"\n')
    
 
    #
    # Catch anything not matching anything else
    #
    @pdcli.catchall
    def catchall(self):
        self.outfd('"help" for a list of all commands\n')

# Get stuff out of the arguments
p = setupArgParse()
args = p.parse_args()

addr = args.addr
port = args.port
guid = args.guid

if(not guid):
    if('DEVID' in os.environ):
        guid = os.environ['DEVID']
        out.info('Setting devid = %s based on DEVID environment variable\n' % guid)

if(not guid):
    out.warn('No developer ID set, please set "DEVID" environment variable or provide -g option\n')
    exit()

###############################################################################
## Main loop
###############################################################################
url = 'http://%s:%s/v1/' % (addr, port)
out.info('Connecting to API server: %s\n' % url)
clt = client.ParaDropAPIClient(devid=guid, url=url)
out.prompt = Stdout()
pdcmd = PDCommands(sys.stdin, out.prompt, clt)

pdcmd.run()
