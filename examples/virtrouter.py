###################################################################
# Copyright 2013-2014 All Rights Reserved
# Authors: The Paradrop Team
###################################################################

from lib.paradrop import chute

loadme = 'virtRouter'

virtRouter = chute.Chute()

#
# Set info data about this chute
#
virtRouter.name = "MyVirtualRouter0"
virtRouter.devinfo = {"description": "This is a simple virtual router"}

#
# Set structure of chute
#
virtRouter.struct = {
  "disk": {
    "size": 123456
  },
  "net": {
    "wan": {
      "type": "wan",
      "intfName": "eth0",
      "ipaddr": "10.100.10.1",
      "netmask": "255.255.255.0" 
    },
    "wifi": {
      "type": "wifi" ,
      "intfName": "eth1",
      "ipaddr": "10.100.11.1",
      "netmask": "255.255.255.0",
      "ssid": "Virtual0",
      "encryption": "psk2",
      "key": "wifi1234" 
    }
  }
} 

#
# Set runtime of chute
#
virtRouter.runtime = [
  {
    "name": "forwarding",
    "program": "@net.runtime.rule(eth1, eth0, 10.100.11.1, masq)",
  },
  {
    "name": "webhosting",
    "program": "uhttpd",
    "args": "-p 80 -i .php=/usr/bin/php-cgi -h /srv/www" 
  },
  {
    'name': 'DHCP Server',
    'program': '@net.runtime.dhcpserver'
  }
]

#
# Set traffic of chute
#
virtRouter.traffic = [
]

#
# Set resources of chute
#
virtRouter.resource = {
  "cpu": "@resource.cpu.DEFAULT",
  "memory": '@resource.memory.DEFAULT',
  "wan": {"down": 25000, "up": 10000},
  "wifi": {"down": 25000, "up": 10000}
}

#
# Set files of chute
#
virtRouter.files = [
]

