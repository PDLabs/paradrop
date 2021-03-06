###################################################################
# Copyright 2013-2014 All Rights Reserved
# Authors: The Paradrop Team
###################################################################


from lib.paradrop import chute

loadme = 'seccamChute'

seccamChute = chute.Chute()

#
# Set info data about this chute
#
seccamChute.name = "SecCam"

#
# Set structure of chute
#
seccamChute.struct = {
  "disk": {
    "size": 12345
  },
  "net": {
    "wan": {
      "type": "wan",
      "intfName": "eth0",
      "ipaddr": "10.100.12.1",
      "netmask": "255.255.255.0" 
    },
    "wifi": {
      "type": "wifi" ,
      "intfName": "eth1",
      "ipaddr": "10.100.13.1",
      "netmask": "255.255.255.0",
      "ssid": "SecCam",
      "encryption": "psk2",
      "key": "wifi1234" 
    }
  }
} 

#
# Send files over to chute
#
seccamChute.files = [
  {
    "name":"www",
    "path":"/srv/www",
    "location":"@paradrop.server(seccam/srv.tar.gz)",
    "sha1":"526bb8cb52458aad4043c56980cd238551b46b7e",
    "todo":"EXTRACT"
  },
  {
    "name":"root",
    "path":"/root",
    "sha1":"1633ea1d6351929cc2c8717d1611dcb41681b585",
    "location":"@paradrop.server(seccam/seccam.py)",
  }
]

#
# Set runtime of chute
#
seccamChute.runtime = [
  {
    "name": "webhosting",
    "program": "uhttpd",
    "args": "-p 80 -i .php=/usr/bin/php-cgi -h /srv/www" 
  },
  {
    "name": "DHCP Server",
    "program": "@net.runtime.dhcpserver"
  }
]


#
# Set traffic of chute
#
seccamChute.traffic = [
  {
    "name": "Web",
    "description": "Allows the chute to provide a webserver on WAN",
    "rule": "@net.traffic.redirect(@net.host.lan:*:5000, wifi:10.100.13.1:80)"
  },
  {
    "name": "HostSSH",
    "description": "Allows the host stack access to SSH",
    "rule": "@net.traffic.redirect(@net.host.lan:*:5001, wifi:10.100.13.1:22)"
  }
]

#
# Set resources of chute
#
seccamChute.resource = {
  "cpu": 1024,
  "memory": 53687091,
  "wan": {"down": 25000, "up": 25000},
  "wifi": {"down": 25000, "up": 25000}
}

