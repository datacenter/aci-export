#!/bin/python
################################################################################
#               _    ____ ___      _____                       _               #
#              / \  / ___|_ _|    | ____|_  ___ __   ___  _ __| |_             #
#             / _ \| |    | |_____|  _| \ \/ / '_ \ / _ \| '__| __|            #
#            / ___ \ |___ | |_____| |___ >  <| |_) | (_) | |  | |_             #
#           /_/   \_\____|___|    |_____/_/\_\ .__/ \___/|_|   \__|            #
#                                            |_|                               #
#                                                                              #
#                   == Cisco ACI Configuration Export tool ==                  #
#                                                                              #
################################################################################
#                                                                              #
# [+] Written by:                                                              #
#  |_ Luis Martin (lumarti2@cisco.com)                                         #
#  |_ CITT Software CoE.                                                       #
#  |_ Cisco Advanced Services, EMEAR.                                          #
#                                                                              #
################################################################################
#                                                                              #
# Copyright (c) 2015-2016 Cisco Systems                                        #
# All Rights Reserved.                                                         #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, this software  #
#    is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF   #
#    ANY KIND, either express or implied.                                      #
#                                                                              #
################################################################################

# External library imports
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import netifaces
from acitoolkit.acitoolkit import Session, Credentials
from acifabriclib import Fabric

# Internal library imports
from tools import *

# Standard library imports
import time
import threading

# Default values
DEFAULT_FTP_PORT=21
DEFAULT_FTP_ADDR="127.0.0.1"
DEFAULT_KEY="fskj5b13qlkj09fsiqc"
DEFAULT_USER="aciexport"
DEFAULT_PWD="45099d87gsd984shf3s"

# Global variables
g_do_exit=False
g_recv_file=None

# CLASS DEFINITIONS
class OneTimeFTPHandler(FTPHandler):
    """
    Custom FTP Handler to detect when the APIC has finished sending the export
    file. When that happens, the pyftpdlib library will call the 
    on_file_received()
    """
    def on_file_received(self, file):
        """
        This method is called when the FTP server has received a full file. 
        Here we just change the state of two global variables so the main
        process can detect that we already have the file we wanted and we can
        start wrapping up.
        """
        global g_do_exit
        global g_recv_file
        g_do_exit=True
        g_recv_file=file

class FTPListener(threading.Thread):
    """
    Simple thread to run the FTP Server
    """
    def __init__(self, user=DEFAULT_USER, pwd=DEFAULT_PWD, port=DEFAULT_FTP_PORT, addr=DEFAULT_FTP_ADDR):
        """
        Constructor
        """
        self.user=user
        self.pwd=pwd
        self.port=port
        self.addr=addr
        threading.Thread.__init__(self)

    def run(self):
        """
        Starts the FTP server
        """
        authorizer = DummyAuthorizer()
        authorizer.add_user(self.user, self.pwd, ".", perm="elradfmw")
        handler = OneTimeFTPHandler
        handler.authorizer = authorizer
        self.server = FTPServer((self.addr, self.port), handler)
        self.server.serve_forever()
        
    def stop(self):
        """
        Stops the FTP server
        """
        if self.server is not None:
            self.server.close()

class ConfExportPolicy():
    """
    This class represents all relevant APIC policy for configuration export
    """
    def __init__(self, addr, port=DEFAULT_FTP_PORT, key=DEFAULT_KEY, user=DEFAULT_USER, pwd=DEFAULT_PWD):
        self.addr = addr
        self.port = port
        self.key  = key
        self.user = user
        self.pwd  = pwd
        
    def create_remote_location(self):
        """
        Returns the URL and the XML data for the creation of a new remote location.
        The name of the remote location is always "TMP-FTP-SERVER"
        """
        txt=[]
        txt.append('<fileRemotePath host="%s" name="TMP-FTP-SERVER" protocol="ftp" remotePort="%i" userName="%s" userPasswd="%s">' % (self.addr, self.port, self.user, self.pwd))
        txt.append('    <fileRsARemoteHostToEpg tDn="uni/tn-mgmt/mgmtp-default/oob-default" />')
        txt.append('</fileRemotePath>')
        url = "api/node/mo/uni/fabric/path-TMP-FTP-SERVER.xml"
        return {'url' : url, 'data' : "\n".join(txt)}
    
    def create_encryption_key(self):
        """
        Returns the URL and the XML data for the creation of a new encyption key
        to be used to encrypt exported configuration data.
        """
        txt=[]
        txt.append('<pkiExportEncryptionKey dn="uni/exportcryptkey" strongEncryptionEnabled="yes" passphrase="%s" />' % self.key)
        url = '/api/node/mo/uni/exportcryptkey.xml'
        return {'url' : url, 'data' : "\n".join(txt)}
    
    def create_config_export(self):
        """
        Returns the URL and the XML data for the creation of a new configuration
        export policy. The name of the policy is always "TMP-CONF-EXPORT-Pol"
        """
        txt=[]
        txt.append('<configExportP adminSt="triggered" dn="uni/fabric/configexp-TMP-CONF-EXPORT-Pol" format="xml" includeSecureFields="yes" name="TMP-CONF-EXPORT-Pol" >')
        txt.append('    <configRsRemotePath tnFileRemotePathName="TMP-FTP-SERVER" />')
        txt.append('</configExportP>')
        url = "/api/node/mo/uni/fabric/configexp-TMP-CONF-EXPORT-Pol.xml"
        return {'url' : url, 'data' : "\n".join(txt)}
    
    def _get_fabric_objects(self):
        """
        This method returns a list of XML objects that can be pushed to 
        the fabric in order to make the information contained in this object
        persistent.
        @return a list of dictionaries, where each dictionary contains two
        entries: 'data', which contains XML-encoded data, and 'url', which
        contains the API URL that needs to be used to POST the data. Note that 
        URLs do not contain the address of the APIC, but only the relative 
        path from there.
        (e.g. /api/node/mo/uni/fabric/configexp-TMP-CONF-EXPORT-Pol.xml)
        """
        objects_to_push = []
        objects_to_push.append(self.create_remote_location())
        objects_to_push.append(self.create_encryption_key())
        objects_to_push.append(self.create_config_export())
        return objects_to_push


class ACIExport():
    """
    This class represents the ACI-Export tool. It contains the program's "main"
    function and a few helper methods.
    """
    @staticmethod
    def run():
        # Argument parsing. We use the ACI toolkit logic here, which tries to
        # retrieve credentials from the following places:
        # 1. Command line options
        # 2. Configuration file called credentials.py
        # 3. Environment variables
        # 4. Interactively querying the user
        # At the end, we should have an object args with all the necessary info.
        description = 'APIC credentials'
        creds = Credentials('apic', description)
        creds.add_argument('-d', "--debug", default=None, help='Enable debug mode')
        creds.add_argument('-A', "--address", default=None, help='Local IP address')
        creds.add_argument('-P', "--port", default=None, help='Local Port for FTP connections')
        creds.add_argument('-K', "--key", default=None, help='ACI encryption key')
        args = creds.get()
        
        # Print welcome banner
        ACIExport.print_banner()
        
        # Let's check if the user passed all relevant parameters
        if args.debug is not None:
            debug_enable()
        if args.address is None:
            # If the user didn't pass any IP address, let's figure out what IPs we
            # have configured locally. If it's only one, use it. Otherwise, ask
            # the user interactively to pick one
            candidates={}
            for iface in netifaces.interfaces():
                for addr in netifaces.ifaddresses(iface):
                    addr_str = netifaces.ifaddresses(iface)[addr][0]['addr']
                    # Skip IPv6 addresses
                    if addr_str.count(":")>0:
                        continue
                    # Skip localhost and unassigned addresses
                    elif addr_str=="0.0.0.0" or addr_str=="127.0.0.1":
                        continue
                    # Skip Microsoft auto-assigned addresses
                    elif addr_str.startswith("169.254."):
                        continue
                    else:
                        candidates[addr_str]=addr_str
            output("Please indicate which local IP address should be used (enter its sequence number):")
            for i in range(0, len(candidates)):
                print(" -> [%i] %s" % (i,candidates.keys()[i]))
            answer=-1
            while( not (answer>=0 and answer<len(candidates)) ):
                try:
                    answer = int(input("$: "))
                except:
                    continue
            args.address = candidates[candidates.keys()[answer]]
            output("Address selected: %s" % args.address)
        if args.port is None:
            args.port = DEFAULT_FTP_PORT
        else:
            args.port=int(args.port)
        if args.key is None:
            args.key = DEFAULT_KEY
    
        # Now, we log into the APIC
        fabric = Fabric(args.url, args.login, args.password)
        fabric.connect()
    
        # Instance our FTP server    
        ftplistener = FTPListener(addr=args.address, port=args.port)
        ftplistener.daemon = True
        ftplistener.start()
        
        # Nasty thing: sleep for 1 sec to give enough time to the FTP server to
        # initialize @todo: use decent concurrency control mechanisms
        time.sleep(1)
        
        # Push config to the fabric
        pols = ConfExportPolicy(addr=args.address, port=args.port, key=args.key)
        fabric.push_to_apic(pols)
        
        output("Waiting for the ACI fabric to send its configuration export file...")
        while g_do_exit is False:
            time.sleep(1)
        
        output("File '%s' was successfully received. Closing..." % g_recv_file)
        
        output("Please make a note of the encryption key: '%s'" % args.key)
        
        # Finally, stop the server and quit
        ftplistener.stop()

        return True

    @staticmethod
    def print_banner():
        output("        _    ____ ___      _____                       _    ", start="")
        output("       / \  / ___|_ _|    | ____|_  ___ __   ___  _ __| |_  ", start="")
        output("      / _ \| |    | |_____|  _| \ \/ / '_ \ / _ \| '__| __| ", start="")
        output("     / ___ \ |___ | |_____| |___ >  <| |_) | (_) | |  | |_  ", start="")
        output("    /_/   \_\____|___|    |_____/_/\_\ .__/ \___/|_|   \__| ", start="")
        output("                                     |_|                    ", start="")
        output("                                                            ", start="")
        output("          == Cisco ACI Configuration Export tool =        \n", start="")


# Start of the execution
if __name__ == "__main__":
    ACIExport.run()
    sys.exit(0)
