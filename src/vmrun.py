# Copyright 2009-2015 VMware, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess
import sys
import string
from utils import *
from ovfenv import *

vmrunInstance = None

def initializeVmrunInstance():
    global vmrunInstance
    vmrunInstance = VmrunCommand("")
    
def getVmrunInstance():
    global vmrunInstance
    return vmrunInstance

class VmrunCommand:
    
    def __init__(self, toolsPath=""):
        self.toolsPath = toolsPath
        self.vmrunCmd = "vmrun"  # We assume it is in the path
        self.mkisofsCmd = "mkisofs"
        self.vdiskmanagerCmd = "vmware-vdiskmanager"
    
    def powerOn(self, vmxPath):
        guiOption = "nogui"
        if GetCmdOption("gui", False):
            guiOption = "gui"
        cmd = [ self.vmrunCmd, "start", vmxPath, guiOption ]
        self.subprocessCall(cmd)
    
    def powerOff(self, vmxPath, hard=False):
        if hard:
            action = "hard"
        else:
            action ="soft"
        cmd = [ self.vmrunCmd, "stop", vmxPath, action ]
        self.subprocessCall(cmd)                              
    
    def subprocessCall(self, cmd):
        try:
            subprocess.call(cmd)
        except:
            print "Error: Failed to execute " + cmd[0] + ". Is it in your path?"
            sys.exit(1)
            
    def readRuntimeVariable(self, vmxPath, name):
        cmd = [ self.vmrunCmd,
                "readVariable",
                vmxPath,
                "runtimeConfig",
                name]
        pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
        out = pipe.read().strip().lower()
        pipe.close()
        return out.strip()
    
    def readGuestInfoIp(self, vmxPath):
        return self.readRuntimeVariable(vmxPath, "guestinfo.ip")
    
    def getIP(self, vmxPath):
        out = self.readGuestInfoIp(vmxPath)
        if out.find("error") != -1:
            return "" # Not running
        return out.strip()
    
    def getPowerStateAndIp(self, vmxPath):
        out = self.readGuestInfoIp(vmxPath)
        if out.find("error") != -1:
            return ("Powered Off", "")
        if len(out) == 0:
            return ("Powered On", "")
        else:
            return ("Powered On", out)
    
    def getInstallDir(self):
        return os.path.dirname(sys.argv[0])
                    
    def createVm(self, vmxFile, name, memSize, diskSize):
        dir = os.path.dirname(vmxFile)
        cleanupList = OsMkdirs(dir)
                
        diskFile = os.path.join(dir, "disk.vmdk")
        success = self.createSparseVmdk(diskFile, diskSize)
        if not success:
            cleanupList.reverse()
            for dir in cleanupList:
                OsTryRmdir(dir)
                sys.exit(1)
        
        self.createVmxFile(vmxFile, name, memSize, diskFile)
        
    def createSparseVmdk(self, filename, diskSize):
        diskCreatePath = os.path.join(self.toolsPath, self.vdiskmanagerCmd)
        OsTryRemove(filename)
        cmd = [ diskCreatePath,
                "-c",
                "-t", "0",              # monoSparse
                "-s", diskSize + "GB",  # capacity
                "-a", "lsilogic",       # adapter type
                filename]
        try:
            subprocess.call(cmd)
        except:
            print "Error: Failed to execute " + cmd[0] + ". Is it in your path?"
            return False
        return True
        
    def createVmxFile(self, vmxPath, name, memSize, diskFile):
        vmxTemplatePath = os.path.join(self.getInstallDir(), "template.vmx")
        vmxTemplateFile = open(vmxTemplatePath, "r")
        vmxTemplate = Template(vmxTemplateFile.read())
        vmxTemplateFile.close()
        
        # Make diskFile relative to vmx file
        diskFile = CreateRelPath(os.path.dirname(vmxPath), diskFile)
        
        subMap = {
           "name"      : name,
           "diskName"  : diskFile,
           "memory"    : memSize }
        
        vmx =  vmxTemplate.substitute(subMap)
        
        OsTryRemove(vmxPath)
        vmxFile = open(vmxPath, "w")
        print >> vmxFile, vmx
        vmxFile.close()
    
    def vmxEscape(self, str):
        escaped = [ '#', '|', '\\', '"']
        
        def escape(c):
            if c in escaped or ord(c) < 32:
                return "|%02x" % ord(c)
            else:
                return c
        
        return "".join(map(escape, str))
        
    def splitVmxEntry(self, line):
        s = line.split("=")        
        if len(s) < 2:
            return ("", "")            
        return (s[0].strip().lower(), s[1].strip().lower())
    
    def getBoolVmxKey(self, vmxDict, key, defval=False):
        if not key in vmxDict: return defval
        val = vmxDict[key]
        return val == '"true"' or val == "true"
    
    def getVmxKey(self, vmxDict, key, defval=""):
        if not key in vmxDict: return defval
        return vmxDict[key]
                                           
    def readVmxFile(self, vmxFile):        
        vmxDict = {}
        vmxIn = open(vmxFile, "r")        
        for line in vmxIn:
            line = line[:-1] # Drop ending
            (key, value) = self.splitVmxEntry(line)
            if key != "":
                vmxDict[key] = value
        return vmxDict
    
    def detectCdRomDevice(self, vmxFile):
        vmxDict = self.readVmxFile(vmxFile)
                                
        devices = [ "ide" + str(x) + ":" + str(y) for x in range(0,2) for y in range(0,2)] + \
                  [ "scsi" + str(x) + ":" + str(y) for x in range(0,8) for y in range(0,8)]
    
        devices = filter(lambda x: self.isCdromDevice(vmxDict, x), devices)
        
        candidate = None        
        for dev in devices:
            if self.isMoutingOvfEnvIso(vmxDict, dev):
                return dev
            
            if candidate == None and self.isCdromCandidate(vmxDict, dev):
                candidate = dev
        
        return candidate                
                                        
    def isCdromDevice(self, vmxDict, device):                           
        if not self.getBoolVmxKey(vmxDict, device + ".present"):                    
            return False
        
        deviceType = self.getVmxKey(vmxDict, device + ".devicetype")
        if not deviceType in ['"atapi-cdrom"', '"cdrom-raw"', '"cdrom-image"']:            
            return False;
        
        return True
    
    def isCdromCandidate(self, vmxDict, dev):
        startConnected = self.getBoolVmxKey(vmxDict, ".startconnected")
        if not startConnected: return True
        deviceType = self.getVmxKey(vmxDict, dev + ".devicetype")
        filename = self.getVmxKey(vmxDict, dev + ".filename")
        if deviceType == '"cdrom-image"':
            return filename == ""
        return True
                    
    def isMoutingOvfEnvIso(self, vmxDict, dev):        
        deviceType = self.getVmxKey(vmxDict, dev + ".devicetype")
        filename = self.getVmxKey(vmxDict, dev + "filename")
        return deviceType == '"cdrom-image"' and filename == '"ovf-env.iso"'
                          
    def patchVmxFile(self, vmxFile, ovfEnv, transport):
        (dir, basename) = os.path.split(vmxFile)
        (name, ext) = os.path.splitext(basename)
        
        transport = map(string.lower, transport)
        doIso = "iso" in transport
        doGuestInfo = "com.vmware.guestinfo" in transport
        if not doIso and not doGuestInfo:
            doIso = doGuestInfo = True
        
        dropKeys = set(["guestinfo.ovfenv",
                       "msg.autoanswer"])
        endBlock = ""
  
        # Generate ISO
        if doIso:
            ovfEnvIsoFile = os.path.join(dir, "ovf-env.iso")
            createOvfEnvIso(ovfEnvIsoFile, self.mkisofsCmd, ovfEnv)
        
            # Detect CD ROM device
            device = self.detectCdRomDevice(vmxFile)
            if device == None:
                print "Error: No cdrom device found for OVF environment in VM", vmxFile
                sys.exit(-1)
                                    
            # Save ovf-env to be nice
            ovfEnvFile = os.path.join(dir, "ovf-env.xml")
            WriteTxtFile(ovfEnvFile, ovfEnv)
    
            dropKeys.add(device + ".filename")
            dropKeys.add(device + ".devicetype")
            dropKeys.add(device + ".autodetect")
            dropKeys.add(device + ".startconnected")
            dropKeys.add(device + ".present")
                                                                           
            endBlock += '''
msg.autoAnswer = "TRUE"
%s.fileName = "ovf-env.iso"
%s.deviceType = "cdrom-image"
%s.startConnected = "TRUE"
%s.present = "TRUE"
''' % (device, device, device, device)

        if doGuestInfo:
            endBlock += '''
guestinfo.ovfEnv = "%s"
''' % (self.vmxEscape(ovfEnv))
        
        self.rewriteVmxFile(vmxFile, dropKeys, endBlock)
 
    def disconnectOvfIsoInVmx(self, vmxFile, transport):
        (dir, basename) = os.path.split(vmxFile)
        (name, ext) = os.path.splitext(basename)
        
        # No need to unmount if we didn't mount it
        transport = map(string.lower, transport)
        doIso = "iso" in transport        
        if not doIso:
            return;
                    
        # Detect CD ROM device      
        device = self.detectCdRomDevice(vmxFile)
        if device == None:
            return
            
        dropKeys = set([device + "startconnected"])
        endBlock = device + '.startConnected="FALSE"'
        
        self.rewriteVmxFile(vmxFile, dropKeys, endBlock)                                         

    def rewriteVmxFile(self, vmxFile, dropKeys, endBlock):
        # Rewrite VMX file
        newVmxFile = vmxFile + ".rewritten"
        vmxIn = open(vmxFile, "r")
        vmxOut = open(newVmxFile, "w")
        for line in vmxIn:
            line = line[:-1]
            key, value = self.splitVmxEntry(line)                                
            if key in dropKeys:                
                continue
            print >> vmxOut, line
        
        print >> vmxOut, endBlock
        
        vmxIn.close()
        vmxOut.close()
        
        oldVmxFile = vmxFile + ".old"
        OsTryRemove(oldVmxFile)
        os.rename(vmxFile, oldVmxFile)
        os.rename(newVmxFile, vmxFile)
 
