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

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import os
import subprocess
import sys
import string

from pkg_resources import (ResourceManager, get_provider)

from .commands import vmrunCmd, vdiskmanagerCmd
from .utils import (GetCmdOption, OsMkdirs, OsTryRmdir, OsTryRemove,
                    CreateRelPath, WriteTxtFile)
from .ovfenv import createOvfEnvIso

vmrunInstance = None

# See http://www.py2exe.org/index.cgi/Py2ExeSubprocessInteractions
# This does not adversely affect vapprun behavior.
if sys.platform.startswith('win'):
    NUL_STDERR = open('nul', 'a')
else:
    NUL_STDERR = None


def initializeVmrunInstance():
    global vmrunInstance
    vmrunInstance = VmrunCommand()


def getVmrunInstance():
    global vmrunInstance
    return vmrunInstance


class VmrunCommand:

    def powerOn(self, vmxPath):
        guiOption = "nogui"
        if GetCmdOption("gui", False):
            guiOption = "gui"
        cmd = [vmrunCmd, "start", vmxPath, guiOption]
        self.subprocessCall(cmd)

    def powerOff(self, vmxPath, hard=False):
        if hard:
            action = "hard"
        else:
            action = "soft"
        cmd = [vmrunCmd, "stop", vmxPath, action]
        self.subprocessCall(cmd)

    def subprocessCall(self, cmd, exitOnFail=True):
        try:
            # On Windows, inhibit the console window that
            # pops up as a result of doing this.
            if sys.platform.startswith('win'):
                import win32process
                opts = {'creationflags': win32process.CREATE_NO_WINDOW}
            else:
                opts = {}
            subprocess.call(cmd, **opts)
        except:
            print("Error: Failed to execute ", cmd[0], ". Is it in your path?")
            if exitOnFail:
                sys.exit(1)
            return False

        return True

    def readRuntimeVariable(self, vmxPath, name):
        cmd = [vmrunCmd,
               "readVariable",
               vmxPath,
               "runtimeConfig",
               name]
        # We pipe stdin even though we don't write anything to it,
        # and use NUL_STDERR (on Windows, an explicit nul-pointing
        # file handle.) This is to work around issues with py2exe
        # and does not harm behavior on non-Windows platforms.
        # Furthermore, on Windows, inhibit the console window that
        # pops up as a result of doing this.
        if sys.platform.startswith('win'):
            import win32process
            opts = {'creationflags': win32process.CREATE_NO_WINDOW}
        else:
            opts = {}

        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             stderr=NUL_STDERR,
                             **opts)
        out = p.stdout.read().strip().lower()
        p.stdout.close()
        return out.strip()

    def readGuestInfoIp(self, vmxPath):
        return self.readRuntimeVariable(vmxPath, "guestinfo.ip")

    def getIP(self, vmxPath):
        out = self.readGuestInfoIp(vmxPath)
        if out.find("error") != -1:
            return ""  # Not running
        return out.strip()

    def getPowerStateAndIp(self, vmxPath):
        out = self.readGuestInfoIp(vmxPath)
        if out.find("error") != -1:
            return ("Powered Off", "")
        if len(out) == 0:
            return ("Powered On", "")
        else:
            return ("Powered On", out)

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
        OsTryRemove(filename)
        cmd = [vdiskmanagerCmd,
               "-c",
               "-t", "0",              # monoSparse
               "-s", diskSize + "GB",  # capacity
               "-a", "lsilogic",       # adapter type
               filename]

        return self.subprocessCall(cmd, exitOnFail=False)

    def getTemplate(self, fname):
        current_module = sys.modules[__name__]
        provider = get_provider(current_module.__package__)
        manager = ResourceManager()

        p = "/".join(['templates', fname])

        if not provider.has_resource(p):
            raise Exception("Template not found: %s", fname)

        return provider.get_resource_string(manager, p)

    def createVmxFile(self, vmxPath, name, memSize, diskFile):
        vmxTemplateString = self.getTemplate('template.vmx')
        vmxTemplate = string.Template(vmxTemplateString)

        # Make diskFile relative to vmx file
        diskFile = CreateRelPath(os.path.dirname(vmxPath), diskFile)

        subMap = {"name": name,
                  "diskName": diskFile,
                  "memory": memSize}

        vmx = vmxTemplate.substitute(subMap)

        OsTryRemove(vmxPath)
        with open(vmxPath, "w") as vmxFile:
            print(vmx, file=vmxFile)

    def vmxEscape(self, str):
        escaped = ['#', '|', '\\', '"']

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
        if key not in vmxDict:
            return defval
        val = vmxDict[key]
        return val == '"true"' or val == "true"

    def getVmxKey(self, vmxDict, key, defval=""):
        if key not in vmxDict:
            return defval
        return vmxDict[key]

    def readVmxFile(self, vmxFile):
        vmxDict = {}
        vmxIn = open(vmxFile, "r")
        for line in vmxIn:
            line = line[:-1]  # Drop ending
            (key, value) = self.splitVmxEntry(line)
            if key != "":
                vmxDict[key] = value
        return vmxDict

    def detectCdRomDevice(self, vmxFile):
        vmxDict = self.readVmxFile(vmxFile)

        devices = (["ide" + str(x) + ":" + str(y)
                    for x in range(0, 2) for y in range(0, 2)] +
                   ["scsi" + str(x) + ":" + str(y)
                    for x in range(0, 8) for y in range(0, 8)])

        devices = filter(lambda x: self.isCdromDevice(vmxDict, x), devices)

        candidate = None
        for dev in devices:
            if self.isMoutingOvfEnvIso(vmxDict, dev):
                return dev

            if candidate is None and self.isCdromCandidate(vmxDict, dev):
                candidate = dev

        return candidate

    def isCdromDevice(self, vmxDict, device):
        if not self.getBoolVmxKey(vmxDict, device + ".present"):
            return False

        deviceType = self.getVmxKey(vmxDict, device + ".devicetype")
        if deviceType not in ['"atapi-cdrom"', '"cdrom-raw"', '"cdrom-image"']:
            return False

        return True

    def isCdromCandidate(self, vmxDict, dev):
        startConnected = self.getBoolVmxKey(vmxDict, ".startconnected")
        if not startConnected:
            return True
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
            createOvfEnvIso(ovfEnvIsoFile, ovfEnv)

            # Detect CD ROM device
            device = self.detectCdRomDevice(vmxFile)
            if device is None:
                print("Error: No cdrom device found for OVF environment in VM",
                      vmxFile)
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
            return

        # Detect CD ROM device
        device = self.detectCdRomDevice(vmxFile)
        if device is None:
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
            print(line, file=vmxOut)

        print(endBlock, file=vmxOut)

        vmxIn.close()
        vmxOut.close()

        oldVmxFile = vmxFile + ".old"
        OsTryRemove(oldVmxFile)
        os.rename(vmxFile, oldVmxFile)
        os.rename(newVmxFile, vmxFile)
