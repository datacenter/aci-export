
               _    ____ ___      _____                       _
              / \  / ___|_ _|    | ____|_  ___ __   ___  _ __| |_
             / _ \| |    | |_____|  _| \ \/ / '_ \ / _ \| '__| __|
            / ___ \ |___ | |_____| |___ >  <| |_) | (_) | |  | |_ 
           /_/   \_\____|___|    |_____/_/\_\ .__/ \___/|_|   \__|
                                            |_|

                   == Cisco ACI Configuration Export tool ==

Introduction
=============
ACI-Export is a simple tool to export fabric configuration directly to a local
local computer (versus having to set up an FTP server somewhere and fetching
the file from there). 

Basically, it spans a temporary FTP server locally, sets up an on-demand 
configuration export job on the fabric, receives the configuration export file
and exits.


Requirements
=============
- Python 2.7
- pyftpdlib library
  - https://github.com/giampaolo/pyftpdlib/archive/master.zip
- Netifaces library (0.10.4 or higher)
  - https://pypi.python.org/packages/source/n/netifaces/netifaces-0.10.4.tar.gz
- The "acifabriclib" library
  - Download it from the following URL and install it using "python2.7 setup.py install"
    - https://github.com/datacenter/acifabriclib
- The "acitoolkit" library
  - Download it from the following URL and install it using "python2.7 setup.py install"
    - https://github.com/datacenter/acitoolkit

Usage
=====

    $ ./aci-export.py --help
    usage: aci-export.py [-h] [-u URL] [-l LOGIN] [-p PASSWORD]
                         [-d DEBUG] [-A ADDRESS] [-P PORT] [-K KEY]
    
    optional arguments:
      -h, --help                        show this help message and exit
      -u URL, --url URL                 APIC IP address.
      -l LOGIN, --login LOGIN           APIC login ID.
      -p PASSWORD, --password PASSWORD  APIC login password.
      -d DEBUG, --debug DEBUG           Enable debug mode
      -A ADDRESS, --address ADDRESS     Local IP address
      -P PORT, --port PORT              Local Port for FTP connections (def 21)
      -K KEY, --key KEY                 ACI encryption key


    $ aci-export.py

The application also parses any existing *credentials.py* file stored in the
same directory. In that case, the content of the *credentials.py* file must 
follow this format:

    URL="https://192.168.0.90"
    LOGIN="admin"
    PASSWORD="Ap1cPass123"

If the *credentials.py* does not exist and the credentials are not supplied from
the command line, the application will ask for them interactively.

Usage Examples
==============
    $ python2.7 aci-export.py
    $ python2.7 aci-export.py --debug yes
    $ python2.7 aci-export.py  -l admin -p "Ap1cPass123" -u "https://192.168.0.90"
    $ python2.7 aci-export.py -A 192.168.0.25
    $ python2.7 aci-export.py -A 192.168.0.25 -P 3388
    $ python2.7 aci-export.py -K "ThisIsMyEncryptionKey"


Output Examples
===============
    $ ./aci-export.py
            _    ____ ___      _____                       _
           / \  / ___|_ _|    | ____|_  ___ __   ___  _ __| |_
          / _ \| |    | |_____|  _| \ \/ / '_ \ / _ \| '__| __|
         / ___ \ |___ | |_____| |___ >  <| |_) | (_) | |  | |_
        /_/   \_\____|___|    |_____/_/\_\ .__/ \___/|_|   \__|
                                         |_|
    
              == Cisco ACI Configuration Export tool =
    
    [+] Please indicate which local IP address should be used (enter its sequence number):
     -> [0] 192.168.88.1
     -> [1] 192.168.202.1
     -> [2] 10.148.90.167
     -> [3] 192.168.56.1
    $: 2
    [+] Address selected: 10.148.90.167
    [I 2015-10-28 17:40:24] >>> starting FTP server on 10.148.90.167:21, pid=5640 <<<
    [I 2015-10-28 17:40:24] poller: <class 'pyftpdlib.ioloop.Poll'>
    [I 2015-10-28 17:40:24] masquerade (NAT) address: None
    [I 2015-10-28 17:40:24] passive ports: None
    [I 2015-10-28 17:40:24] use sendfile(2): False
    [+] Waiting for the ACI fabric to send its configuration export file...
    [I 2015-10-28 17:40:32] 10.48.59.238:40501-[] FTP session opened (connect)
    [I 2015-10-28 17:40:32] 10.48.59.238:40501-[aciexport] USER 'aciexport' logged in.
    [I 2015-10-28 17:40:32] 10.48.59.238:40501-[aciexport] CWD /home/lumarti2/repos/aci-utils/aci-export 250
    [I 2015-10-28 17:40:32] 10.48.59.238:40501-[aciexport] STOR ce_TMP-CONF-EXPORT-Pol-2015-10-28T17-40-50.tar.gz completed=1 
    bytes=84277 seconds=0.156
    [I 2015-10-28 17:40:32] 10.48.59.238:40501-[aciexport] FTP session closed (disconnect).
    [+] File 'ce_TMP-CONF-EXPORT-Pol-2015-10-28T17-40-50.tar.gz' was successfully received. Closing...
    [+] Please make a note of the encryption key: 'fskj5b13qlkj09fsiqc'


