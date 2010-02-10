set cmd=python %VAPPRUN%\src\vapprun.py 

%cmd% create-vapp LAMP
%cmd% def-property LAMP "key=ws_ip" "type=ip:Network"
%cmd% def-property LAMP "key=db_ip" "type=ip:Network"
%cmd% def-property LAMP "key=netmask" "type=expression" "value=${netmask:Network}"
%cmd% def-property LAMP "key=gateway" "type=expression" "value=${gateway:Network}"
%cmd% def-property LAMP "key=hostprefix" "type=expression" "value=${hostPrefix:Network}"
%cmd% def-property LAMP "key=dns" "type=expression" "value=${dns:Network}"
%cmd% def-property LAMP "key=searchpath" "type=expression" "value=${searchPath:Network}"

%cmd% link-vm webVM "vmx=C:\VMs\LampWebVM\webVm.vmx"
%cmd% edit  webVM "parent=LAMP"
%cmd% edit  webVM "startOrder=20" "startWait=320" "waitForTools=True" "stopWait=320"

%cmd% link-vm dbVM "vmx=C:\VMs\LampDbVm\dbVm.vmx"
%cmd% edit  dbVM "parent=LAMP"
%cmd% edit  dbVM "startOrder=10" "startWait=320" "waitForTools=True" "stopWait=320"


%cmd% edit LAMP "appUrl=http://${ws_ip}/"
%cmd% edit dbVM "appUrl=http://${db_ip}/phpmyadmin/"

%cmd% set-property -transient LAMP

rem %cmd% set-property -fixed LAMP "ws_ip=192.168.1.40" "db_ip=192.168.1.41"

