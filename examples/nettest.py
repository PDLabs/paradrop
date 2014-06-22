###################################################################
# Copyright 2013-2014 All Rights Reserved
# Authors: The Paradrop Team
###################################################################

from lib.paradrop import chute

loadme = 'netChute'

netChute = chute.Chute()

netChute.name = "NetTest"

#
# Set structure of chute
#
netChute.struct = {
  "disk": {
    "size": 123456
  },
  "net": {
    "wan": {
      "type": "wan",
      "intfName": "eth0",
      "ipaddr": "10.100.14.1",
      "netmask": "255.255.255.0" 
    }
  }
} 

#
# Send files over to chute
#
netChute.files = [  
 { 
    "name":"speedtest",
    "path":"/root/test",
    "sha1":"93f29dc9974cdcf8afd5a5071fed66315a5301cf",
    "location":"@paradrop.server(nettest/speedtest.tar.gz)",
    "todo":"EXTRACT"
 },
 { 
    "name":"www",
    "path":"/srv/www",
    "sha1":"c26e50da520702856bfd3935ccf1ee4f0c71094f",
    "location":"@paradrop.server(nettest/www.tar.gz)",
    "todo":"EXTRACT"
 } 
]

#
# Set runtime of chute
#
netChute.runtime = [
  {
    "name": "Run Speedtest Script",
    "program": "python /root/test/dumpdb.py",
    "cron":"*/5 * * * *"
  },
  {
    "name": "webhosting",
    "program": "uhttpd",
    "args": "-p 80 -i .php=/usr/bin/php-cgi -h /srv/www" 
  }
]


#
# Set traffic of chute
#
netChute.traffic = [
  {
    "name": "Webserver",
    "description": "Allows the host to access the webserver",
    "rule": "@net.traffic.redirect(@net.host.lan:*:5100, wan:10.100.14.1:80)"
  },
  {
    "name": "HostSSH",
    "description": "Allows the host stack access to SSH",
    "rule": "@net.traffic.redirect(@net.host.lan:*:5101, wan:10.100.14.1:22)"
  }
]

#
# Set resources of chute
#
netChute.resource = {
  "cpu": 15,
  "memory": 53687091,
  "wan": {"down": '@resource.net.wan.down.MAX', "up": '@resource.net.wan.up.MAX'},
}

