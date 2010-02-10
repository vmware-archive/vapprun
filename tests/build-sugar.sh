#!/bin/bash
vapprun create-vapp SugarCRM

vapprun def-property SugarCRM key=webIp         type=ip:Network
vapprun def-property SugarCRM key=dbIp          type=ip:Network
vapprun def-property SugarCRM key=dns           type=expression value=\${dns:Network}
vapprun def-property SugarCRM key=domainName    type=expression value=\${domainName:Network}
vapprun def-property SugarCRM key=searchPath type=expression value=\${searchPath:Network}
vapprun def-property SugarCRM key=gateway       type=expression value=\${gateway:Network}
vapprun def-property SugarCRM key=netmask       type=expression value=\${netmask:Network}
vapprun def-property SugarCRM key=hostPrefix    type=expression value=\${hostPrefix:Network}
vapprun def-property SugarCRM key=emailAdmin    type=string
vapprun def-property SugarCRM key=theme         type=string value=Retro
vapprun def-property SugarCRM key=concurrentSessions type=int

vapprun link-vm  SugarDB vmx=/Users/renes/VMs/SugarCRM/db/dbVm.vmx
vapprun edit   SugarDB parent=SugarCRM
vapprun edit   SugarDB startOrder=10 startWait=400 waitForTools=True stopWait=400
vapprun def-property SugarDB key=ip type=expression value=\${dbIp}

vapprun link-vm  SugarWeb vmx=/Users/renes/VMs/SugarCRM/web/webVm.vmx
vapprun edit   SugarWeb parent=SugarCRM
vapprun edit   SugarWeb startOrder=20 startWait=370 waitForTools=True stopWait=370
vapprun def-property SugarWeb key=ip2 type=expression value=\${webIp}

vapprun edit   SugarCRM appUrl=http://\${webIp}/crm

vapprun set-property  -transient SugarCRM


