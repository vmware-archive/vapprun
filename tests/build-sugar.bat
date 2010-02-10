
set cmd=python %VAPPRUN%\src\vapprun.py 

%cmd% create-vapp SugarCRM

%cmd% def-property SugarCRM "key=webIp"         "type=ip:Network"
%cmd% def-property SugarCRM "key=dbIp"          "type=ip:Network"
%cmd% def-property SugarCRM "key=dns"           "type=expression" "value=${dns:Network}"
%cmd% def-property SugarCRM "key=domainName"    "type=expression" "value=${domainName:Network}"
%cmd% def-property SugarCRM "key=searchPath" "type=expression" "value=${searchPath:Network}"
%cmd% def-property SugarCRM "key=gateway"       "type=expression" "value=${gateway:Network}"
%cmd% def-property SugarCRM "key=netmask"       "type=expression" "value=${netmask:Network}"
%cmd% def-property SugarCRM "key=hostPrefix"    "type=expression" "value=${hostPrefix:Network}"
%cmd% def-property SugarCRM "key=emailAdmin"    "type=expression"
%cmd% def-property SugarCRM "key=theme"         "type=expression" "value=Retro"
%cmd% def-property SugarCRM "key=concurrentSessions" "type=int"

%cmd% link-vm  SugarDB "vmx=C:\VMs\SugarCRM\db\dbVm.vmx"
%cmd% edit   SugarDB "parent=SugarCRM"
%cmd% edit   SugarDB "startOrder=10" "startWait=400" "waitForTools=True" "stopWait=400"
%cmd% def-property SugarDB "key=ip" "type=string" "value=${dbIp}"

%cmd% link-vm  SugarWeb "vmx=C:\VMs\SugarCRM\web\webVm.vmx"
%cmd% edit   SugarWeb "parent=SugarCRM"
%cmd% edit   SugarWeb "startOrder=20" "startWait=370" "waitForTools=True" "stopWait=370"
%cmd% def-property SugarWeb "key=ip2" "type=string" "value=${webIp}"

%cmd% edit   SugarCRM "appUrl=http://${webIp}/crm"

%cmd% set-property -transient SugarCRM


