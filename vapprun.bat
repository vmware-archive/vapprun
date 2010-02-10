rem -- Copyright 2009-2015 VMware, Inc. All Rights Reserved.
rem -- 
rem -- Licensed under the Apache License, Version 2.0 (the "License");
rem -- you may not use this file except in compliance with the License.
rem -- You may obtain a copy of the License at
rem -- 
rem --     http://www.apache.org/licenses/LICENSE-2.0
rem -- 
rem -- Unless required by applicable law or agreed to in writing, software
rem -- distributed under the License is distributed on an "AS IS" BASIS,
rem -- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
rem -- See the License for the specific language governing permissions and
rem -- limitations under the License.

@echo OFF

SETLOCAL 

rem --
rem -- SETUP VAPPRUN_HOME
rem --
IF DEFINED VAPPRUN_HOME goto s1
set VAPPRUN_HOME=%~dp0

:s1
if NOT EXIST "%VAPPRUN_HOME%" goto errorVApprun

rem --
rem -- SETUP VMWARE_HOME 
rem --
IF DEFINED VMWARE_HOME goto s2

SET VMWARE_HOME=C:\Program Files (x86)\VMware
IF EXIST "%VMWARE_HOME%" goto s2
SET VMWARE_HOME=C:\Program Files\VMware
IF NOT EXIST "%VMWARE_HOME%" goto errorVMware

:s2
rem --
rem -- SETUP PYTHON_CMD
rem --
SET PYTHON_CMD=python.exe
IF NOT DEFINED PYTHON_HOME goto s3:
set PYTHON_CMD=%PYTHON_HOME%\python.exe
IF NOT EXIST "%PYTHON_CMD%" goto errorPython

:s3
rem -- 
rem -- Add mkisofs.exe, vmware-vdiskmanager, and vmrun.exe to the path --
rem -- 
SET PATH=%VMWARE_HOME%\VMware VIX;%PATH%
SET PATH=%VMWARE_HOME%\VMware Workstation;%PATH%


%PYTHON_CMD% %VAPPRUN_HOME%\src\vapprun.py %1 %2 %3 %4 %5 %6 %7
goto end


:errorVMware
echo "VMWARE_HOME variable must be set"
goto end


:errorVapprun
echo "VAPPRUN_HOME variable must be set"
goto end

:errorPython
echo "PYTHON_HOME is not valid"
goto end

:end
