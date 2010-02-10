#!/bin/bash
vapprun create-vapp LAMP
vapprun def-property LAMP key=ws_ip    type=ip:Network
vapprun def-property LAMP key=db_ip    type=ip:Network
vapprun def-property LAMP key=netmask  type=expression value=\${netmask:Network}
vapprun def-property LAMP key=gateway  type=expression value=\${gateway:Network}
vapprun def-property LAMP key=hostprefix type=expression value=\${hostPrefix:Network}
vapprun def-property LAMP key=dns type=expression value=\${dns:Network}
vapprun def-property LAMP key=dnssearchpath type=expression value=\${searchPath:Network}

vapprun link-vm webVM vmx=/Users/renes/VMs/LampWebVM/webVm.vmx
vapprun edit  webVM parent=LAMP
vapprun edit  webVM startOrder=20 startWait=320 waitForTools=True stopWait=320

vapprun link-vm dbVM vmx=/Users/renes/VMs/LampDbVm/dbVm.vmx
vapprun edit  dbVM parent=LAMP
vapprun edit  dbVM startOrder=10 startWait=320 waitForTools=True stopWait=320

vapprun set-property -fixed LAMP ws_ip=192.168.1.40 db_ip=192.168.1.41

