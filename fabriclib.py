################################################################################
#                                                                              #
#                   _____     _          _      _     _ _                      #
#                  |  ___|_ _| |__  _ __(_) ___| |   (_) |__                   #
#                  | |_ / _` | '_ \| '__| |/ __| |   | | '_ \                  #
#                  |  _| (_| | |_) | |  | | (__| |___| | |_) |                 #
#                  |_|  \__,_|_.__/|_|  |_|\___|_____|_|_.__/                  #
#                                                                              #
#                       === ACI Fabric Setup Library ===                       #
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
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, this software  #
#    is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF   #
#    ANY KIND, either express or implied.                                      #
#                                                                              #
################################################################################

# Standard Library Imports
import sys
import json

# Internal library Imports
from tools import *

# External Library Imports
import requests
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

# == Classes included in this library ==
# 
#  +----------+    +--------------------+       +------------------+
#  |  Fabric  |    | InterfacePolicies  |.......| GenericInterface |
#  +----------+    +--------------------+       +------------------+
#                                                  ^      ^       ^
#  +----------------+                              |      |       |
#  |  ACIException  |                  +-----------+      |       +------+
#  +----------------+                  |                  |              |
#                               +------+-------+  +-------+-------+  +---+---+
#                               |  AccessPort  |  |  PortChannel  |  |  VPC  |
#                               +--------------+  +---------------+  +-------+
#

class Fabric():
    """
    This class encapsulates a working session with the ACI fabric
    """
    def __init__(self, url, username, password):
        """
        Constructor
        """
        if not url.startswith("http"):
            self.url = "https://" + url
        else:    
            self.url=url                # APIC's URL
        # Remove trailing "/" if it exists
        if self.url[-1]=="/":
            self.url[:-1]
        self.username=username          # Username
        self.password=password          # Password
        self.auth_cookie=None           # APIC Auth Cookie 

    def connect(self):
        """
        Using the credentials supplied at instantiation time, this method
        establishes and HTTP(s) connection to the fabric an attemps to 
        authenticate. On success, an authentication cookie is stored internally
        so subsequent calls to http_get(), http_post() and push_to_fabric()
        already have the necessary security tokens.
        """
        # Login to APIC
        auth_url=self.url + "/api/aaaLogin.json"
        login_creds={"aaaUser": {"attributes": {"name":self.username, "pwd": self.password}}}
        debug(json.dumps(login_creds))
        
        r=requests.post(auth_url, data=json.dumps(login_creds), verify=False)
        resp_data = json.loads(r.text)
        try:
            # Make sure the returned data is structured the way we expect
            assert('imdata' in resp_data)
            assert('aaaLogin' in resp_data['imdata'][0])
            assert('attributes' in resp_data['imdata'][0]['aaaLogin'])
            assert('token' in resp_data['imdata'][0]['aaaLogin']['attributes'])
            # Check for the auth cookie in the HTTP response
            assert('APIC-cookie' in r.cookies)
        except:
            fatal("[E] ERROR: " + str(resp_data))
        else:
            debug("[+] Connection to APIC at %s performed successfully." % self.url)
            debug("[+] Token: %s" % resp_data['imdata'][0]['aaaLogin']['attributes']['token'])
            # If we get here it means we authenticated successfully. In this case, we'll
            # extract the session cookie returned by the APIC so we can pass it in all
            # subsequent requests (so the controller knows we are a valid authorized user)
            self.auth_cookie = {'APIC-cookie' : r.cookies['APIC-cookie'] }
            debug("[+] Cookie: %s" % r.cookies['APIC-cookie'])

    def _fix_url(self, url):
        """
        Makes sure supplied URL is of the form https://<APIC_ADDRESS>/path, 
        adding the necessary elements if it doesn't
        """
        if not url.startswith("http"):
            if not url.startswith("/"):
                url = self.url + "/" + url
            else:
                url = self.url + url
        return url

    def http_get(self, url):
        """
        Performs an HTTP GET operation against the fabric
        @return on success, returns data received from the server
        @raises ACIException in case of failure
        """
        url = self._fix_url(url)
        r = requests.get(url, cookies=self.auth_cookie, verify=False)
        if r.status_code == 200 :
            r.text
        else:
            raise ACIException(str(r.text))

    def http_post(self, url, data):
        """
        Performs an HTTP POST operation against the fabric
        @return on success, returns None
        @raises ACIException in case of failure
        """
        url = self._fix_url(url)
        r = requests.post(url, data, cookies=self.auth_cookie, verify=False)
        if r.status_code == 200 :
            return None
        else:
            raise ACIException(str(r.text))


    def push_to_apic(self, object_to_push):
        items = object_to_push._get_fabric_objects()
        for i in items:
            debug("POST URL: %s" % i['url'])
            debug(i['data'])
            self.http_post(i['url'], i['data'])


class InterfacePolicies():
    """
    This class represents a standard set of interface policies to be created
    on the fabric. It defines the name of all the policies and allows
    configuration to be easily pushed to the fabric, passing an instance of 
    this class to Fabric.push_to_apic()
    """
    def __init__(self):
        """"
        Constructor. It defines standard names for all policies. Note that 
        the user may choose to alter the name of any given policy simply by accessing
        the relevant class attribute and assigning a different value to it.
        """        
        # CDP Policies
        self.cpd_enabled       = "CDP-Enabled"
        self.cpd_disabled      = "CDP-Disabled"
        
        # LLDP Policies
        self.lldp_enabled      = "LLDP-Enabled"
        self.lldp_disabled     = "LLDP-Disabled"
        
        # LACP Policies
        self.lacp_active       = "LACP-Active"
        self.lacp_passive      = "LACP-Passive"
        self.lacp_off          = "LACP-Off"
        self.lacp_mac          = "LACP-MAC-Pinning"
        
        # MCP Policies
        self.mcp_enabled       = "MCP-Enabled"
        self.mcp_disabled      = "MCP-Disabled"
        
        # STP Policies
        self.stp_bpdu_filter   = "STP-BPDU-Filter"
        self.stp_bpdu_guard    = "STP-BPDU-Guard"
        self.stp_bpdu_all      = "STP-BPDU-All"
        
        # L2 Interface Policies
        self.vlan_scope_port   = "VLAN-Scope-Port"
        self.vlan_scope_global = "VLAN-Scope-Global"
        
        # Distributed Firewall Policies
        self.firewall_enabled  = "Firewall-Enabled"
        self.firewall_disabled = "Firewall-Disabled"
        self.firewall_learning = "Firewall-Learning"

        # Link Level Policies
        self.link_100m_auto    = "Link-100M-Auto"
        self.link_100m_noneg   = "Link-100M-NoNegotiate"
        self.link_1g_auto      = "Link-1G-Auto"
        self.link_1g_noneg     = "Link-1G-NoNegotiate"
        self.link_10g_auto     = "Link-10G-Auto"
        self.link_10g_noneg    = "Link-10G-NoNegotiate"
        self.link_40g_auto     = "Link-40G-Auto"
        self.link_40g_noneg    = "Link-40G-NoNegotiate"


    def _get_fabric_objects(self):
        """
        This method returns a list of XML objects that can be pushed to 
        the fabric in order to make the information contained in this object
        persistent.
        @return a list of dictionaries, where each dictionary contains two
        entries: 'data', which contains XML-encoded data, and 'url', which
        contains the API URL that needs to be used to POST the data. Note that 
        URLs do not contain the address of the APIC, but only the relative 
        path from there (e.g. /api/node/mo/uni/infra/cdpIfP-CPD-Enabled.xml)
        """
        objects_to_push = []
        
        # CDP Policies
        #  -> Enabled
        url='/api/node/mo/uni/infra/cdpIfP-%s.xml' % self.cpd_enabled
        xml = '<cdpIfPol adminSt="enabled" dn="uni/infra/cdpIfP-%s" name="%s" />' % (self.cpd_enabled, self.cpd_enabled)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> Disabled
        url='/api/node/mo/uni/infra/cdpIfP-%s.xml' % self.cpd_disabled
        xml = '<cdpIfPol adminSt="disabled" dn="uni/infra/cdpIfP-%s" name="%s" />' % (self.cpd_disabled, self.cpd_disabled)
        objects_to_push.append( {'url' : url, 'data' : xml} )

        # LLDP Policies
        #  -> Enabled
        url='/api/node/mo/uni/infra/lldpIfP-%s.xml' % self.lldp_enabled
        xml = '<lldpIfPol adminRxSt="enabled" adminTxSt="enabled" dn="uni/infra/lldpIfP-%s" name="%s"/>' % (self.lldp_enabled, self.lldp_enabled)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> Disabled
        url='/api/node/mo/uni/infra/lldpIfP-%s.xml' % self.lldp_disabled
        xml = '<lldpIfPol adminRxSt="enabled" adminTxSt="enabled" dn="uni/infra/lldpIfP-%s" name="%s"/>' % (self.lldp_disabled, self.lldp_disabled)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        
        # LACP Policies
        #  -> Active
        url='/api/node/mo/uni/infra/lacplagp-%s.xml' % self.lacp_active
        xml = '<lacpLagPol ctrl="fast-sel-hot-stdby,graceful-conv,susp-individual" dn="uni/infra/lacplagp-%s" maxLinks="16" minLinks="1" mode="active" name="%s" />' % (self.lacp_active, self.lacp_active)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> Passive
        url='/api/node/mo/uni/infra/lacplagp-%s.xml' % self.lacp_passive
        xml = '<lacpLagPol ctrl="fast-sel-hot-stdby,graceful-conv,susp-individual" dn="uni/infra/lacplagp-%s" maxLinks="16" minLinks="1" mode="passive" name="%s" />' % (self.lacp_passive, self.lacp_passive)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> Off
        url='/api/node/mo/uni/infra/lacplagp-%s.xml' % self.lacp_off
        xml = '<lacpLagPol ctrl="fast-sel-hot-stdby,graceful-conv,susp-individual" dn="uni/infra/lacplagp-%s" maxLinks="16" minLinks="1" mode="off" name="%s" />' % (self.lacp_off, self.lacp_off)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> MAC Pinning
        url='/api/node/mo/uni/infra/lacplagp-%s.xml' % self.lacp_mac
        xml = '<lacpLagPol ctrl="fast-sel-hot-stdby,graceful-conv,susp-individual" dn="uni/infra/lacplagp-%s" maxLinks="16" minLinks="1" mode="mac-pin" name="%s" />' % (self.lacp_mac, self.lacp_mac)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        
        # MCP Policies
        #  -> Enabled
        url='/api/node/mo/uni/infra/mcpIfP-%s.xml' % self.mcp_enabled
        xml = '<mcpIfPol adminSt="enabled" dn="uni/infra/mcpIfP-%s" name="%s" />' % (self.mcp_enabled, self.mcp_enabled)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> Disabled
        url='/api/node/mo/uni/infra/mcpIfP-%s.xml' % self.mcp_disabled
        xml = '<mcpIfPol adminSt="disabled" dn="uni/infra/mcpIfP-%s" name="%s" />' % (self.mcp_disabled, self.mcp_disabled)
        objects_to_push.append( {'url' : url, 'data' : xml} )

        # STP Policies
        #  -> BPDU Filter
        url='/api/node/mo/uni/infra/ifPol-%s.xml' % self.stp_bpdu_filter
        xml = '<stpIfPol ctrl="bpdu-filter" dn="uni/infra/ifPol-%s" name="%s" />' % (self.stp_bpdu_filter, self.stp_bpdu_filter)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> BPDU Guard
        url='/api/node/mo/uni/infra/ifPol-%s.xml' % self.stp_bpdu_guard
        xml = '<stpIfPol ctrl="bpdu-guard" dn="uni/infra/ifPol-%s" name="%s" />' % (self.stp_bpdu_guard, self.stp_bpdu_guard)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> BPDU Filter + Guard
        url='/api/node/mo/uni/infra/ifPol-%s.xml' % self.stp_bpdu_all
        xml = '<stpIfPol ctrl="bpdu-filter,bpdu-guard" dn="uni/infra/ifPol-%s" name="%s" />' % (self.stp_bpdu_all, self.stp_bpdu_all)
        objects_to_push.append( {'url' : url, 'data' : xml} )

        # L2 Interface Policies
        #  -> VLAN Port Scope
        url='/api/node/mo/uni/infra/l2IfP-%s.xml' % self.vlan_scope_port
        xml = '<l2IfPol dn="uni/infra/l2IfP-%s" name="%s" vlanScope="portlocal" />' % (self.vlan_scope_port, self.vlan_scope_port)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> VLAN Global Scope
        url='/api/node/mo/uni/infra/l2IfP-%s.xml' % self.vlan_scope_global
        xml = '<l2IfPol dn="uni/infra/l2IfP-%s" name="%s" vlanScope="global" />' % (self.vlan_scope_global, self.vlan_scope_global)
        objects_to_push.append( {'url' : url, 'data' : xml} )

        # Firewall Policies
        #  -> Enabled
        url='/api/node/mo/uni/infra/fwP-%s.xml' % self.firewall_enabled
        xml = '<nwsFwPol dn="uni/infra/fwP-%s" mode="enabled" name="%s" />' % (self.firewall_enabled, self.firewall_enabled)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> Disabled
        url='/api/node/mo/uni/infra/fwP-%s.xml' % self.firewall_disabled
        xml = '<nwsFwPol dn="uni/infra/fwP-%s" mode="disabled" name="%s" />' % (self.firewall_disabled, self.firewall_disabled)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> Learning
        url='/api/node/mo/uni/infra/fwP-%s.xml' % self.firewall_learning
        xml = '<nwsFwPol dn="uni/infra/fwP-%s" mode="learning" name="%s" />' % (self.firewall_learning, self.firewall_learning)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        
        # Link Level Policies
        #  -> 100M Auto 
        url='/api/node/mo/uni/infra/hintfpol-%s.xml' % self.link_100m_auto
        xml = '<fabricHIfPol autoNeg="on" dn="uni/infra/hintfpol-%s" linkDebounce="100" name="%s" speed="100M" />' % (self.link_100m_auto, self.link_100m_auto)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> 100M NoNegotiate
        url='/api/node/mo/uni/infra/hintfpol-%s.xml' % self.link_100m_noneg
        xml = '<fabricHIfPol autoNeg="off" dn="uni/infra/hintfpol-%s" linkDebounce="100" name="%s" speed="100M" />' % (self.link_100m_noneg, self.link_100m_noneg)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> 1G Auto 
        url='/api/node/mo/uni/infra/hintfpol-%s.xml' % self.link_1g_auto
        xml = '<fabricHIfPol autoNeg="on" dn="uni/infra/hintfpol-%s" linkDebounce="100" name="%s" speed="1G" />' % (self.link_1g_auto, self.link_1g_auto)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> 1G NoNegotiate
        url='/api/node/mo/uni/infra/hintfpol-%s.xml' % self.link_1g_noneg
        xml = '<fabricHIfPol autoNeg="off" dn="uni/infra/hintfpol-%s" linkDebounce="100" name="%s" speed="1G" />' % (self.link_1g_noneg, self.link_1g_noneg)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> 10G Auto 
        url='/api/node/mo/uni/infra/hintfpol-%s.xml' % self.link_10g_auto
        xml = '<fabricHIfPol autoNeg="on" dn="uni/infra/hintfpol-%s" linkDebounce="100" name="%s" speed="10G" />' % (self.link_10g_auto, self.link_10g_auto)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> 10G NoNegotiate
        url='/api/node/mo/uni/infra/hintfpol-%s.xml' % self.link_10g_noneg
        xml = '<fabricHIfPol autoNeg="off" dn="uni/infra/hintfpol-%s" linkDebounce="100" name="%s" speed="10G" />' % (self.link_10g_noneg, self.link_10g_noneg)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> 40G Auto 
        url='/api/node/mo/uni/infra/hintfpol-%s.xml' % self.link_40g_auto
        xml = '<fabricHIfPol autoNeg="on" dn="uni/infra/hintfpol-%s" linkDebounce="100" name="%s" speed="40G" />' % (self.link_40g_auto, self.link_40g_auto)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        #  -> 40G NoNegotiate
        url='/api/node/mo/uni/infra/hintfpol-%s.xml' % self.link_40g_noneg
        xml = '<fabricHIfPol autoNeg="off" dn="uni/infra/hintfpol-%s" linkDebounce="100" name="%s" speed="40G" />' % (self.link_40g_noneg, self.link_40g_noneg)
        objects_to_push.append( {'url' : url, 'data' : xml} )
        
        # Template
        #url='/api/node/mo/uni/infra/<OBJTYPE>-%s.xml' % self.
        #xml = '' % (self., self.)
        #objects_to_push.append( {'url' : url, 'data' : xml} )
        
        # @todo: implement the following
        # Monitoring Policies
        # Storm Control Interface Policies
       
        return objects_to_push

class GenericInterface():
    
    """
    This class represents a generic fabric interface. It is not meant to be 
    instanced by the user. Instead, its children "AccessPort", "PortChannel" 
    and "VPC" are expected to do the job.
    """

    def __init__(self, name):
        """
        Constructor
        """
        # Name
        self.name=name
        
        # Description
        self.description=""
        
        # Ports part of this interface
        # _ports must be lists of dictionaries containing the following keys:
        # "node", "card", "port" 
        # For example: {'node': 101, 'card' : 1, 'port' : 38}
        self._ports=[]
        
        # Different nodes we are part of (this will only be more than one
        # for VPCs). _nodes must be a list of integers (e.g. [101, 102])
        self._nodes=[]
        
        # CDP Policy
        self._cdp="default"
        
        # LLDP Policy
        self._lldp="default"

        # STP Policy
        self._stp="default"
        
        # L2 Interface Policy
        self._l2="default"

        # MCP Policy
        self._mcp="default"
        
        # Associated Attachable Entity Profile
        self._aep="default"
        
        # LACP Policy
        self._lacp="default"
        
        # Link Level Policy
        self._link="default"

        # Storm Control Interface Policy
        self._storm="default"

        # Monitoring Policy
        self._monitor="default"
        
        # Distributed Firewall Policy
        self._firewall="default"
        
        # Standard Interface policies to reference
        self._ifpols = InterfacePolicies()

    def add_port(self, node_id, card, port):
        """
        Associates a particular port with tis interface. This will add
        a new port to a list. Then the appropriate children will interpret those 
        Note that "node_id", "card" and "port" must all be integers 
        (e.g. add_port(101, 1, 20))
        """
        node = int(node_id)
        card = int(card)
        port = int(port)
        self._ports.append({'node':node, 'card':card, 'port':port})
        if node not in self._nodes:
            self._nodes.append(node)

    def associate_aep(self, aep_name):
        """
        Associates this VPC with an existing Attachable Entity Profile
        """
        self._aep=aep_name

    def custom_interface_policies(self, policies):
        """
        Allows the user to pass their own instance of InterfacePolicies, so
        different interface policy names can be used.
        @param policies must be of type InterfacePolicies
        """
        self._ifpols = policies

    def cdp_enabled(self):
        """
        Enables CDP on this interface
        """
        self._cdp = self._ifpols.cpd_enabled
        return self._cdp
    
    def cdp_disabled(self):
        """
        Disables CDP on this interface
        """
        self._cdp = self._ifpols.cpd_disabled
        return self._cdp

    def lldp_enabled(self):
        """
        Enables LLDP on this interface
        """
        self._lldp = self._ifpols.lldp_enabled
        return self._lldp

    def lldp_disabled(self):
        """
        Disables LLDP on this interface
        """
        self._lldp = self._ifpols.lldp_disabled
        return self._lldp
    
    def lacp_active(self):
        """
        Sets LACP Active mode on this interface
        """
        self._lacp = self._ifpols.lacp_active
        return self._lacp
    
    def lacp_passive(self):
        """
        Sets LACP Passive mode on this interface
        """
        self._lacp = self._ifpols.lacp_passive
        return self._lacp

    def lacp_off(self):
        """
        Sets LACP Off mode on this interface
        """
        self._lacp = self._ifpols.lacp_off
        return self._lacp

    def lacp_mac_pinning(self):
        """
        Sets LACP MAC Pinning mode on this interface
        """
        self._lacp = self._ifpols.lacp_mac
        return self._lacp
    
    def stp_bpdu_guard(self):
        """
        Enables STP BPDU Guard on this interface
        """
        # If we are already doing BPDU Filter, set up both
        if self._stp in [self._ifpols.stp_bpdu_filter, self._ifpols.stp_bpdu_all]:
            self._stp = self._ifpols.stp_bpdu_all
        # Otherwise, do only BPDU guard
        else:
            self._stp = self._ifpols.stp_bpdu_guard
        return self._stp
  
    def stp_bpdu_filter(self):
        """
        Enables STP BPDU Filter on this interface
        """
        # If we are already doing BPDU Guard, set up both
        if self._stp in [self._ifpols.stp_bpdu_guard, self._ifpols.stp_bpdu_all]:
            self._stp = self._ifpols.stp_bpdu_all
        # Otherwise, do only BPDU Filter
        else:
            self._stp = self._ifpols.stp_bpdu_filter
        return self._stp
    
    def vlan_scope_port(self):
        """
        Sets per-port VLAN significance on this interface
        """
        self._l2 = self._ifpols.vlan_scope_port
        return self._l2    

    def vlan_scope_global(self):
        """
        Sets global VLAN significance on this interface
        """
        self._l2 = self._ifpols.vlan_scope_global
        return self._l2

    def mcp_enabled(self):
        """
        Enables MCP on this interface
        """
        self._mcp = self._ifpols.mcp_enabled
        return self._mcp

    def mcp_disabled(self):
        """
        Disables MCP on this interface
        """
        self._mcp = self._ifpols.mcp_disabled
        return self._mcp

    def mcp_disabled(self):
        """
        Disables MCP on this interface
        """
        self._mcp = self._ifpols.mcp_disabled
        return self._mcp
    
    def firewall_enabled(self):
        """
        Enables Distributed Firewall on this interface
        """
        self._firewall = self._ifpols.firewall_enabled
        return self._firewall
    
    def firewall_disabled(self):
        """
        Disables Distributed Firewall on this interface
        """
        self._firewall = self._ifpols.firewall_disabled
        return self._firewall
    
    def firewall_learning(self):
        """
        Sets the Distributed Firewall policy for this interface to learning mode
        """
        self._firewall = self._ifpols.firewall_learning
        return self._firewall
    
    def link(self, speed, negotiate):
        """
        Sets the speed and negotiation mode for this interface.
        @param speed must be one of "100M", "1G", "10G" or "40G"
        @param negotiate must be True or False
        """
        if speed not in ["100M", "1G", "10G", "40G"]:
            raise ACIException('link(): Unknown speed. Must be one of "100M", "1G", "10G" or "40G"')
        if negotiate not in [True, False]:
            raise ACIException('link(): Unknown mode. Negotiate parameter must be either True or False')
        
        if speed=="100M" and negotiate==True:
            self._link=self._ifpols.link_100m_auto
        elif speed=="100M" and negotiate==True:
            self._link=self._ifpols.link_100m_auto
        elif speed=="1G" and negotiate==True:
            self._link=self._ifpols.link_1g_auto
        elif speed=="1G" and negotiate==False:
            self._link=self._ifpols.link_1g_noneg
        elif speed=="10G" and negotiate==True:
            self._link=self._ifpols.link_10g_auto
        elif speed=="10G" and negotiate==False:
            self._link=self._ifpols.link_10g_noneg
        elif speed=="40G" and negotiate==True:
            self._link=self._ifpols.link_40g_auto
        elif speed=="40G" and negotiate==False:
            self._link=self._ifpols.link_40g_noneg
        else:
            raise ACIException('link(): This is a bug, please report it.')
        return self._link

class AccessPort(GenericInterface):
    """
    This class represents an access port on a leaf switch. Note that the term
    "access port" here does not mean that the port is configured in access mode
    with a single untagged VLAN, it just means it's a single port, not a PortChannel
    or a VPC. 
    """
    def __init__(self, name):
        """
        Constructor. Note that this class does not have attributes of its own
        but they are all inherited from the superclass, GenericInterface. Also
        note that since this isn't an aggregated link, attributes and methods
        related to LACP are accessible but don't apply.
        """
        super(AccessPort, self).__init__(name)

    def _validate(self):
        """
        Performs basic validation of the data contained in the current instance.
        @raises ACIException in case of error.
        """
        if len(self._nodes)!=1:
            raise ACIException("AccessPort (%s) must contain an interface to exactly one node" % self.name)
        elif len(self._ports)!=1:
            raise ACIException("AccessPort (%s) must contain only one interface" % self.name)

    def _get_fabric_objects(self):
        """
        This method returns a list of XML objects that can be pushed to 
        the fabric in order to make the information contained in this object
        persistent.
        @return a list of dictionaries, where each dictionary contains two
        entries: 'data', which contains XML-encoded data, and 'url', which
        contains the API URL that needs to be used to POST the data. Note that 
        URLs do not contain the address of the APIC, but only the relative 
        path from there (e.g. /api/node/mo/uni/infra/nprof-Leaf101.xml)
        """
        objects_to_push = []

        # Validate ports and other internal data. This will raise an exception
        # if something is wrong.
        self._validate()
        
        # Interface Policy Group for Access Port
        url='/api/node/mo/uni/infra/funcprof/accportgrp-%s.xml' % self.name
        xml = []
        xml.append('<infraAccPortGrp descr="%s" dn="uni/infra/funcprof/accportgrp-%s" name="%s">'  % (self.description, self.name, self.name))
        xml.append('    <infraRsMonIfInfraPol tnMonInfraPolName="%s" />' % self._monitor )
        xml.append('    <infraRsLldpIfPol tnLldpIfPolName="%s" />' % self._lldp )
        xml.append('    <infraRsStpIfPol tnStpIfPolName="%s" />' % self._stp )
        xml.append('    <infraRsL2IfPol tnL2IfPolName="%s" />' % self._l2 )
        xml.append('    <infraRsCdpIfPol tnCdpIfPolName="%s" />' % self._cdp )
        xml.append('    <infraRsMcpIfPol tnMcpIfPolName="%s" />' % self._mcp )
        xml.append('    <infraRsAttEntP tDn="uni/infra/attentp-%s" />' % self._aep )
        xml.append('    <infraRsStormctrlIfPol tnStormctrlIfPolName="%s" />' % self._storm )
        xml.append('    <infraRsHIfPol tnFabricHIfPolName="%s" />' % self._link )
        xml.append('</infraAccPortGrp>')
        objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )

        # One Interface Profile and one Switch profile
        url='/api/node/mo/uni/infra/accportprof-%s.xml' % self.name
        xml = []
        xml.append('<infraAccPortP descr="%s" dn="uni/infra/accportprof-%s" name="%s">' % (self.description, self.name, self.name))
        xml.append('    <infraHPortS descr="" name="%s" type="range">' % self.name)
        xml.append('        <infraRsAccBaseGrp fexId="101" tDn="uni/infra/funcprof/accportgrp-%s" />' % self.name)
        card = self._ports[0]['card']
        port = self._ports[0]['port']
        xml.append('        <infraPortBlk fromCard="%i" fromPort="%i" name="%s" toCard="%i" toPort="%i" />' % (card, port, self.name, card, port)) 
        xml.append('    </infraHPortS>')
        xml.append('</infraAccPortP>')
        objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )
        
        # Switch Profile
        sp_name="Leaf-%i" % self._nodes[0]
        url='/api/node/mo/uni/infra/nprof-%s.xml' % sp_name
        xml = []
        xml.append('<infraNodeP dn="uni/infra/nprof-%s" name="%s">' % (sp_name, sp_name))
        xml.append('    <infraLeafS name="leaf-%i" type="range">' % self._nodes[0])
        xml.append('        <infraNodeBlk from_="%i" name="leaf-%i" to_="%i" />' % (self._nodes[0],self._nodes[0],self._nodes[0]))
        xml.append('    </infraLeafS>')
        xml.append('    <infraRsAccPortP tDn="uni/infra/accportprof-%s" />' % self.name)
        xml.append('</infraNodeP>')
        objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )
        
        return objects_to_push

class PortChannel(GenericInterface):
    """
    This class represents a PortChannel aggregated interface on a leaf switch. 
    """
    def __init__(self, name):
        """
        Constructor. Note that this class does not have attributes of its own
        but they are all inherited from the superclass, GenericInterface.
        """
        super(PortChannel, self).__init__(name)

    def _validate(self):
        """
        Performs basic validation of the data contained in the current instance.
        @raises ACIException in case of error.
        """
        if len(self._nodes)!=1:
            raise ACIException("PortChannel (%s) must contain interfaces to exactly one node" % self.name)
    
    def _get_fabric_objects(self):
        """
        This method returns a list of XML objects that can be pushed to 
        the fabric in order to make the information contained in this object
        persistent.
        @return a list of dictionaries, where each dictionary contains two
        entries: 'data', which contains XML-encoded data, and 'url', which
        contains the API URL that needs to be used to POST the data. Note that 
        URLs do not contain the address of the APIC, but only the relative 
        path from there (e.g. /api/node/mo/uni/infra/nprof-Leaf101.xml)
        """
        objects_to_push = []

        # Validate ports and other internal data. This will raise an exception
        # if something is wrong.
        self._validate()
        
        # Interface Policy Group for PortChannel
        url='/api/node/mo/uni/infra/funcprof/accbundle-%s.xml' % self.name
        xml = []
        xml.append('<infraAccBndlGrp descr="%s" dn="uni/infra/funcprof/accbundle-%s" lagT="link" name="%s">' % (self.description, self.name, self.name))
        xml.append('    <infraRsMonIfInfraPol tnMonInfraPolName="%s" />' % self._monitor )
        xml.append('    <infraRsLldpIfPol tnLldpIfPolName="%s" />' % self._lldp )
        xml.append('    <infraRsStpIfPol tnStpIfPolName="%s" />' % self._stp )
        xml.append('    <infraRsL2IfPol tnL2IfPolName="%s" />' % self._l2 )
        xml.append('    <infraRsCdpIfPol tnCdpIfPolName="%s" />' % self._cdp )
        xml.append('    <infraRsMcpIfPol tnMcpIfPolName="%s" />' % self._mcp )
        xml.append('    <infraRsAttEntP tDn="uni/infra/attentp-%s" />' % self._aep )
        xml.append('    <infraRsLacpPol tnLacpLagPolName="%s" />' % self._lacp )
        xml.append('    <infraRsStormctrlIfPol tnStormctrlIfPolName="%s" />' % self._storm )
        xml.append('    <infraRsHIfPol tnFabricHIfPolName="%s" />' % self._link )
        xml.append('</infraAccBndlGrp>')
        objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )
        
        # One Interface Profile and one Switch profile
        url='/api/node/mo/uni/infra/accportprof-%s.xml' % self.name
        xml = []
        xml.append('<infraAccPortP descr="%s" dn="uni/infra/accportprof-%s" name="%s">' % (self.description, self.name, self.name))
        xml.append('    <infraHPortS descr="" name="%s" type="range">' % self.name)
        xml.append('        <infraRsAccBaseGrp fexId="101" tDn="uni/infra/funcprof/accbundle-%s" />' % self.name)
        for i in range(0, len(self._ports)):
            card = self._ports[i]['card']
            port = self._ports[i]['port']
            block_name = "%s-%i" % (self.name, i)
            xml.append('        <infraPortBlk fromCard="%i" fromPort="%i" name="%s" toCard="%i" toPort="%i" />' % (card, port, block_name, card, port)) 
        xml.append('    </infraHPortS>')
        xml.append('</infraAccPortP>')
        objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )
        
        # Switch Profile
        sp_name="Leaf-%i" % self._nodes[0]
        url='/api/node/mo/uni/infra/nprof-%s.xml' % sp_name
        xml = []
        xml.append('<infraNodeP dn="uni/infra/nprof-%s" name="%s">' % (sp_name, sp_name))
        xml.append('    <infraLeafS name="leaf-%i" type="range">' % self._nodes[0])
        xml.append('        <infraNodeBlk from_="%i" name="leaf-%i" to_="%i" />' % (self._nodes[0],self._nodes[0],self._nodes[0]))
        xml.append('    </infraLeafS>')
        xml.append('    <infraRsAccPortP tDn="uni/infra/accportprof-%s" />' % self.name)
        xml.append('</infraNodeP>')
        objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )
        
        return objects_to_push

class VPC(GenericInterface):
    """
    This class represents a VPC aggregated interface on two different leaf switches. 
    """
    def __init__(self, name):
        """
        Constructor. Note that this class does not have attributes of its own
        but they are all inherited from the superclass, GenericInterface.
        """
        super(VPC, self).__init__(name)

    def _validate(self):
        """
        Performs basic validation of the data contained in the current instance.
        @raises ACIException in case of error.
        """
        if len(self._nodes)!=2:
            raise ACIException("VPC (%s) must contain interfaces to exactly two different nodes" % self.name)

    def _get_fabric_objects(self):
        """
        This method returns a list of XML objects that can be pushed to 
        the fabric in order to make the information contained in this object
        persistent.
        @return a list of dictionaries, where each dictionary contains two
        entries: 'data', which contains XML-encoded data, and 'url', which
        contains the API URL that needs to be used to POST the data. Note that 
        URLs do not contain the address of the APIC, but only the relative 
        path from there (e.g. /api/node/mo/uni/infra/nprof-Leaf101.xml)
        """
        objects_to_push = []
        
        # First of all, we need to figure out what kind of scheme we need to 
        # implement. The easiest scenario is the following:
        # 
        # SCENARIO-A:
        #
        #  +---------------+            +---------------+
        #  |   Leaf-101    |            |   Leaf-102    |
        #  +---------------+            +---------------+
        #           1/10 \                / 1/10
        #                 \              /
        #                  \            /
        #                   \          /
        #                  +------------+
        #                  |  Endpoint  |
        #                  +------------+
        #
        # where the ports on the leaves are identical. In this case, we can
        # instance a single switch profile that covers both leaves, and a single
        # interface profile that references port 1/10.
        #
        # If this isn't the case, then we need to go fancy:
        #
        # SCENARIO-B:
        #
        #  +---------------+            +---------------+
        #  |   Leaf-101    |            |   Leaf-102    |
        #  +---------------+            +---------------+
        #           1/10 \                / 1/44
        #                 \              /
        #                  \            /
        #                   \          /
        #                  +------------+
        #                  |  Endpoint  |
        #                  +------------+
        #
        # and create one switch profile and one interface profile per leaf.
        
        # Validate ports and other internal data. This will raise an exception
        # if something is wrong.
        self._validate()
        
        # Parse the list of ports to figure out if we have scenario "A" or "B"
        scenario="A"
        for i in range(0, len(self._ports)):
            # For each port, let's figure out if we have an equivalent one for 
            # the other leaf
            equivalent=False
            for j in range(0, len(self._ports)):
                if i!=j:
                    if self._ports[j]['card']==self._ports[i]['card']:
                        if self._ports[j]['port']==self._ports[i]['port']:
                            if self._ports[j]['node']!=self._ports[i]['node']:
                                equivalent=True
                            else:
                                raise ACIException("Duplicate port detected on VPC %s" % self.name)
            if equivalent==False:
                scenario="B"
                break
        
        # Now let's create some XML
        # Interface Policy Group for VPC (same XML for both scenarios)
        url='/api/node/mo/uni/infra/funcprof/accbundle-%s.xml' % self.name
        xml = []
        xml.append('<infraAccBndlGrp descr="%s" dn="uni/infra/funcprof/accbundle-%s" lagT="node" name="%s">' % (self.description, self.name, self.name))
        xml.append('    <infraRsMonIfInfraPol tnMonInfraPolName="%s" />' % self._monitor )
        xml.append('    <infraRsLldpIfPol tnLldpIfPolName="%s" />' % self._lldp )
        xml.append('    <infraRsStpIfPol tnStpIfPolName="%s" />' % self._stp )
        xml.append('    <infraRsL2IfPol tnL2IfPolName="%s" />' % self._l2 )
        xml.append('    <infraRsCdpIfPol tnCdpIfPolName="%s" />' % self._cdp )
        xml.append('    <infraRsMcpIfPol tnMcpIfPolName="%s" />' % self._mcp )
        xml.append('    <infraRsAttEntP tDn="uni/infra/attentp-%s" />' % self._aep )
        xml.append('    <infraRsLacpPol tnLacpLagPolName="%s" />' % self._lacp )
        xml.append('    <infraRsStormctrlIfPol tnStormctrlIfPolName="%s" />' % self._storm )
        xml.append('    <infraRsHIfPol tnFabricHIfPolName="%s" />' % self._link )
        xml.append('</infraAccBndlGrp>')
        objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )

        # SCENARIO A: Enpoint connected to the same port(s) on both leaves
        if scenario=="A":
            # Common Interface Profile for both leaves
            url='/api/node/mo/uni/infra/accportprof-%s.xml' % self.name
            xml = []
            xml.append('<infraAccPortP descr="%s" dn="uni/infra/accportprof-%s" name="%s">' % (self.description, self.name, self.name))
            xml.append('    <infraHPortS descr="" name="%s" type="range">' % self.name)
            xml.append('        <infraRsAccBaseGrp fexId="101" tDn="uni/infra/funcprof/accbundle-%s" />' % self.name)
            for i in range(0, len(self._ports)):
                # Only do for one of the nodes to avoid duplicates
                if self._ports[i]['node']==self._nodes[0]:
                    card = self._ports[i]['card']
                    port = self._ports[i]['port']
                    block_name = "%s-%i" % (self.name, i)
                    xml.append('        <infraPortBlk fromCard="%i" fromPort="%i" name="%s" toCard="%i" toPort="%i" />' % (card, port, block_name, card, port)) 
            xml.append('    </infraHPortS>')
            xml.append('</infraAccPortP>')
            objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )
            
            # Switch Profile
            if self._nodes[0] < self._nodes[1]:
                sp_name="Leaves-%i-%i" % (self._nodes[0], self._nodes[1])
            else:
                sp_name="Leaves-%i-%i" % (self._nodes[1], self._nodes[0])
            url='/api/node/mo/uni/infra/nprof-%s.xml' % sp_name
            xml = []
            xml.append('<infraNodeP dn="uni/infra/nprof-%s" name="%s">' % (sp_name, sp_name))
            for i in range(0, len(self._nodes)):
                xml.append('    <infraLeafS name="leaf-%i" type="range">' % self._nodes[i])
                xml.append('        <infraNodeBlk from_="%i" name="leaf-%i" to_="%i" />' % (self._nodes[i], self._nodes[i], self._nodes[i]))
                xml.append('    </infraLeafS>')
            xml.append('    <infraRsAccPortP tDn="uni/infra/accportprof-%s" />' % self.name)
            xml.append('</infraNodeP>')
            objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )

        # SCENARIO B: Enpoint connect to different ports on the leaves
        else:
            # One Interface Profile and Switch profile per leaf
            for node in self._nodes:
                ip_name = "%s-%i" % (self.name, node)
                url='/api/node/mo/uni/infra/accportprof-%s.xml' % ip_name
                xml = []
                xml.append('<infraAccPortP descr="%s" dn="uni/infra/accportprof-%s" name="%s">' % (self.description, ip_name, ip_name))
                xml.append('    <infraHPortS descr="" name="%s" type="range">' % ip_name)
                xml.append('        <infraRsAccBaseGrp fexId="101" tDn="uni/infra/funcprof/accbundle-%s" />' % self.name)
                for i in range(0, len(self._ports)):
                    # Pick ports for the current node
                    if self._ports[i]['node']==node:
                        card = self._ports[i]['card']
                        port = self._ports[i]['port']
                        block_name = "%s-%i" % (ip_name, i)
                        xml.append('        <infraPortBlk fromCard="%i" fromPort="%i" name="%s" toCard="%i" toPort="%i" />' % (card, port, block_name, card, port)) 
                xml.append('    </infraHPortS>')
                xml.append('</infraAccPortP>')
                objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )
                
                # Switch Profile
                sp_name="Leaf-%i" % node
                url='/api/node/mo/uni/infra/nprof-%s.xml' % sp_name
                xml = []
                xml.append('<infraNodeP dn="uni/infra/nprof-%s" name="%s">' % (sp_name, sp_name))
                xml.append('    <infraLeafS name="leaf-%i" type="range">' % node)
                xml.append('        <infraNodeBlk from_="%i" name="leaf-%i" to_="%i" />' % (node, node, node))
                xml.append('    </infraLeafS>')
                xml.append('    <infraRsAccPortP tDn="uni/infra/accportprof-%s" />' % ip_name)
                xml.append('</infraNodeP>')
                objects_to_push.append( {'url' : url, 'data' : "\n".join(xml)} )

        return objects_to_push


class ACIException(Exception):
    """
    Exception raised by this tool
    """
    # Exception Constructor
    def __init__(self, err_msg, extra_info=None):
        self.err_msg = err_msg
        self.extra_info = extra_info

    # String conversion operator
    def __str__(self):
        if self.extra_info is not None:
            return self.get_all()
        else:
            return self.get_error()

    # Return a string representation of the error that raised the exception
    def get_error(self):
        return self.err_msg

    # Returns all information available of the error that raised the exception
    # (as a string)
    def get_all(self):
        return str(self.err_msg) + " (%s)" %  str(self.extra_info)

  