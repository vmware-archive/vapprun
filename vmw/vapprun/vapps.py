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

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import re
import sys
import time
from abc import ABCMeta, abstractmethod

from six import add_metaclass

from .ippool import CreateIpPool
from .ovfenv import OvfEnv
from .utils import (BoolToStr, CreateRelPath, GetCmdOption, NewXmlNode,
                    NewXmlTextNode, OsFileList, OsFileListRemove, OsTryRemove,
                    ReadXmlDoc, StrToBool)
from .vmrun import getVmrunInstance

WORKSPACE_CFG_NAME = "vapprun.cfg"
VM_CFG_NAME = "vm.cfg"
VAPP_CFG_NAME = "vapp.cfg"

# Bumped if the XML format is changed in an incompatible way
# (this is checked by ovftool)
VAPPRUN_CONFIG_VERSION = "1"

# Global reference to vApp Inventory
vappsInstance = None


class abstractclassmethod(classmethod):

    __isabstractmethod__ = True

    def __init__(self, callable):
        callable.__isabstractmethod__ = True
        super(abstractclassmethod, self).__init__(callable)


class Property(object):

    def __init__(self, key="", typ="", value="", userConfig=True):
        self.key = key
        self.type = typ
        self.value = value
        self.userConfig = userConfig
        if self.isMacro():
            self.userConfig = False

    def asXmlNode(self):
        if self.isMacro():
            self.userConfig = False
        return NewXmlNode("property") \
            .setAttr("key", self.key)  \
            .setAttr("type", self.type) \
            .setAttr("value", self.value) \
            .setAttr("userConfigurable", BoolToStr(self.userConfig))

    def parseMacro(self):
        exp = re.compile(r"^\${([\w\.]+)(:([\w\.]+))?}$")
        macro = exp.match(self.value)
        if macro is None:
            return (None, None)
        (cmd, dummy, arg) = macro.groups()
        return (cmd, arg)

    def effectiveValue(self, deployParams, parentEnv=None):
        parentEnv = set() if parentEnv is None else parentEnv
        if not self.isMacro():
            val = deployParams[self.key].strip()
            if not self.userConfig or len(val) == 0:
                return self.value
            return val

        (cmd, arg) = self.parseMacro()
        if cmd is None:
            print("Error: Invalid expression '%s' for property '%s'"
                  % (self.value, self.key))
            sys.exit(1)

        if arg is None:
            # Assignment
            if cmd not in parentEnv:
                print("Error: Undefined reference '%s' for property '%s'"
                      % (cmd, self.key))
                sys.exit(1)
            return parentEnv[cmd]
        else:
            if arg != "Network":
                print(("Error: Invalid network name '%s' for property '%s' " +
                       "(it must be 'Network')")
                      % (arg, self.key))
                sys.exit(1)
            (val, found) = getVAppsInstance().ipPool.lookupChildTextNode(cmd)
            if not found:
                print("Error: Invalid expression  '%s' for property '%s'"
                      % (self.value, self.key))
                sys.exit(1)

            return val

        sys.exit(1)

    def isIp(self):
        return self.type.startswith("ip:")

    def isMacro(self):
        return self.type == "expression"

    def isUserConfigurable(self):
        return self.userConfig and not self.isMacro()

    def getAssignee(self):
        (cmd, arg) = self.parseMacro()
        if cmd is None or arg is not None:
            return None
        return cmd


def XmlToProperty(node):
    if node.tag != "property":
        return None

    key = node.getAttr("key")
    typ = node.getAttr("type")
    value = node.getAttr("value")
    userConfig = node.getAttr("userConfigurable")
    if len(key) == 0 or len(typ) == 0:
        return None

    return Property(key, typ, value, StrToBool(userConfig, True))


class Link(object):

    def __init__(self, name, startOrder=30):
        self.name = name
        self.startOrder = startOrder
        self.startWait = 30
        self.stopWait = 30
        self.waitForTools = True

    def asXmlNode(self):
        return NewXmlNode("link")\
            .setAttr("name", self.name)\
            .setAttr("startOrder", self.startOrder)\
            .setAttr("startWait", self.startWait)\
            .setAttr("stopWait", self.stopWait)\
            .setAttr("waitForTools", BoolToStr(self.waitForTools))

    def asString(self):
        return ("[startOrder: %d  startWait: %d waitForTools: %s stopWait: %d]"
                % (self.startOrder, self.startWait,
                   str(self.waitForTools), self.stopWait))


def XmlToLink(node):
    if node.tag != "link":
        return None

    name = node.getAttr("name")
    if len(name) == 0:
        return None

    l = Link(name)
    l.startOrder = node.getAttrInt("startOrder", 1)
    l.startWait = node.getAttrInt("startWait", 30)
    l.waitForTools = node.getAttrBool("waitForTools", True)
    l.stopWait = node.getAttrInt("stopWait", 30)
    return l


class DeployParams(object):

    def __init__(self, allKeys, ipKeys, userKeys, defValues):
        self.config = {}
        self.fileName = None
        self.allKeys = allKeys
        self.ipKeys = ipKeys
        self.userKeys = userKeys
        self.allocationPolicy = "fixed"
        for k in userKeys:
            self.config[k] = ""
        # IP keys are initialized to the empty string,
        # since they might be used by transient or DHCP.
        for k in ipKeys:
            self.config[k] = ""
        for k, v in defValues.items():
            if len(v) > 0:
                self.config[k] = v

    def load(self, fileName):
        node = ReadXmlDoc(fileName)
        if node is None:
            return

        if node.tag != "deployParameters":
            print("Error: Invalid format of file", fileName)
            sys.exit(1)

        self.allocationPolicy = node.getAttr("allocationPolicy",
                                             self.allocationPolicy)

        for n in node.children:
            if n.value is not None and n.tag in self.config:
                self.config[n.tag] = n.value.strip()

        self.fileName = fileName

    def isFixedIpPolicy(self):
        return self.allocationPolicy == "fixed"

    def isDhcpPolicy(self):
        return self.allocationPolicy == "dhcp"

    def isAutoIpKey(self, key):
        return not self.isFixedIpPolicy() and key in self.ipKeys

    def asXmlNode(self):
        root = NewXmlNode("deployParameters") \
            .setAttr("allocationPolicy", self.allocationPolicy)
        for key, value in self.config.items():
            root.addChild(NewXmlTextNode(key, value))
        return root

    def writeToFile(self, fileName=None):
        if fileName is None:
            fileName = self.fileName
        self.asXmlNode().writeToFile(fileName)
        self.fileName = fileName

    def isValidKey(self, key):
        return key in self.config

    def isUserConfigurableKey(self, key):
        return key in self.userKeys and \
            not (key in self.ipKeys and not self.isFixedIpPolicy())

    def setParam(self, key, value):
        self.config[key] = value

    def getParam(self, key):
        if key in self.config:
            return self.config[key]
        else:
            return ""

    def userItems(self):
        l = [(k, v) for (k, v) in self.config.items() if k in self.userKeys]
        if self.isFixedIpPolicy():
            return l
        else:
            return [(k, v) for (k, v) in l if k in self.ipKeys]

    def items(self):
        return self.config.items()

    def empty(self):
        return len(self.config) == 0

    def initIpProps(self, isPowerOn):
        # Check manual mode
        if self.isFixedIpPolicy() and isPowerOn:
            for key in self.ipKeys:
                if self.getParam(key) == "":
                    print("Error: IP property", key, "has no value")
                    sys.exit(1)
            return

        # Clear all IP properties and unreserve IPs
        ipRange = getVAppsInstance().ipRange
        for key in self.ipKeys:
            ipRange.unreserve(self.getParam(key))
            self.setParam(key, "")
        self.writeToFile()

        if self.allocationPolicy == "dhcp" or not isPowerOn:
            return

        # Allocate new values
        for key in self.ipKeys:
            val = ipRange.allocate()
            if val is None:
                print("Error: No IP addresses left in IP pool")
                sys.exit(1)
            self.setParam(key, val)
        self.writeToFile()


@add_metaclass(ABCMeta)
class Entity(object):

    def __init__(self, name, cfgPath):
        self.name = name
        self.cfgPath = cfgPath
        self.dir = os.path.dirname(cfgPath)
        self.link = None
        self.parent = None
        self.children = []
        self.properties = []
        self.state = "unknown"
        self.ip = "unknown"
        self.deployParams = None
        self.tag = ""
        self.appUrl = ""
        self.allocationPolicy = "fixed"
        self.transport = []
        self.ovfEnvProps = None

    @abstractclassmethod
    def isVM(cls):
        return False

    @classmethod
    def isVApp(cls):
        return not cls.isVM()

    def isPoweredOn(self):
        return self.state == "Powered On"

    def load(self):
        node = ReadXmlDoc(self.cfgPath)
        if node.tag != self.getRootTag():
            print("Error reading", self.cfgPath,
                  "Invalid root element:", node.tag)
            sys.exit(1)
        self.loadRootAttributes(node)

        for c in node.children:
            self.loadSection(c)
        self.validate()

    def loadRootAttributes(self, node):
        self.tag = node.getAttr("tag")
        self.appUrl = node.getAttr("appUrl")

    def loadSection(self, node):
        prop = XmlToProperty(node)
        if prop is not None:
            self.properties.append(prop)
            return True

        link = XmlToLink(node)
        if link is not None:
            self.link = link

        return False

    @abstractmethod
    def getRootTag(self):
        pass

    def update(self):
        node = NewXmlNode(self.getRootTag())
        self.writeRootAttributes(node)
        self.writeSections(node)
        node.writeToFile(self.cfgPath)

    def writeRootAttributes(self, node):
        if len(self.tag) > 0:
            node.setAttr("tag", self.tag)
        if len(self.appUrl) > 0:
            node.setAttr("appUrl", self.appUrl)

    def writeSections(self, node):
        if self.link is not None:
            node.addChild(self.link.asXmlNode())

        for p in self.properties:
            node.addChild(p.asXmlNode())

    def getExpandedAppUrl(self, props=None):
        if props is None:
            dp = self.getDeployParams()
            props = dp.config
        expandedAppUrl = self.appUrl
        for (key, value) in props.items():
            macro = "${" + key + "}"
            if self.appUrl.find(macro) >= 0 and value == "":
                return ""
            expandedAppUrl = expandedAppUrl.replace("${" + key + "}", value)
        return expandedAppUrl

    def validate(self):
        pass

    def unsetParent(self):
        if self.link is None:
            return

        if self.parent is not None:
            self.parent.children.remove(self)
        self.parent = None
        self.link = None

    def setParent(self, parent):
        if self.parent == parent:
            return

        if self.parent is not None:
            self.unsetParent()

        link = Link(parent.name)
        self.parent = parent
        self.link = link
        parent.children.append(self)

    def removeDir(self):
        OsTryRemove(os.path.join(self.dir, "deploy.cfg"))
        removeList = []
        self.getUsedFiles(removeList)
        OsFileListRemove(removeList)

    def getUsedFiles(self, usedList):
        if self.parent is None:
            usedList.append((os.path.realpath(os.path.join(self.dir,
                                                           "deploy.cfg")),
                             False))
        usedList.append((os.path.realpath(self.cfgPath), False))
        usedList.append((os.path.realpath(self.dir), True))

    def getPropKeys(self):
        _all = set([p.key for p in self.properties])
        user = set([p.key for p in self.properties if p.isUserConfigurable()])
        ip = set([p.key for p in self.properties if p.isIp()])
        defValues = {}

        for e in self.children:
            (a, _, _, df) = e.getPropKeys()
            _all = _all.union(a)
            user = user.union(user)
            ip = ip.union(ip)
            defValues.update(df)

        for p in self.properties:
            if len(p.value) > 0:
                defValues[p.key] = p.value

        return (_all, ip, user, defValues)

    def getDeployParams(self):

        if self.parent is not None:
            return self.parent.getDeployParams()

        if self.deployParams is not None:
            return self.deployParams

        (allKeys, ipKeys, userKeys, defValues) = self.getPropKeys()
        self.deployParams = DeployParams(allKeys, ipKeys, userKeys, defValues)

        deployCfgFile = os.path.join(self.dir, "deploy.cfg")
        self.deployParams.load(deployCfgFile)
        # We always write it again, since set of properties might have changed
        self.deployParams.writeToFile(deployCfgFile)

        return self.deployParams

    def computeOvfEnvProps(self):
        deployParams = self.getDeployParams()

        parentProps = {}
        props = {}

        if self.parent is not None:
            self.parent.computeOvfEnvProps()
            parentProps = self.parent.ovfEnvProps
            if self.isVM():
                # A VM inherits the properties of the parent, a vApp does not
                props = dict(parentProps)

        for p in self.properties:
            props[p.key] = p.effectiveValue(deployParams.config, parentProps)

        self.ovfEnvProps = props
        return props

    def showOvfEnvProps(self, indent=0):
        if not GetCmdOption("v", False):
            return

        spc = " " * indent
        for key, value in self.ovfEnvProps.items():
            print(spc + "  [" + key, "=", value + "]")

    def getUsedIPs(self):
        deployParam = self.getDeployParams()
        if self.state == "Powered Off" and not deployParam.isFixedIpPolicy():
            return set()

        usedIps = set()
        ipProps = [p for p in self.properties if p.isIp()]
        for p in ipProps:
            val = deployParam.getParam(p.key)
            if val == "":
                val = p.value
            if val != "":
                usedIps.add(val)
        return usedIps

    def propagateIp(self, ip, keysIn=None):
        keysIn = set() if keysIn is None else keysIn
        deployParam = self.getDeployParams()
        keysOut = set()

        for p in self.properties:
            # If an IP value exists, we update the property with the IP address
            if p.isIp() and (len(keysIn) == 0 or p.key in keysIn):
                val = p.effectiveValue(deployParam.config)
                if val == "":
                    deployParam.setParam(p.key, ip)
                    deployParam.writeToFile()
                    return
            else:
                # Keep track of all asignments
                assignee = p.getAssignee()
                keysOut.add(assignee)

        if self.parent and len(keysOut) > 0:
            self.parent.propagateIp(ip, keysOut)

    def inRunningVApp(self):
        if self.state == "Powered On":
            return True
        if self.parent is not None:
            return self.parent.inRunningVApp()
        return False

    def setupIpProperties(self, powerOn):
        if not self.inRunningVApp():
            self.getDeployParams().initIpProps(powerOn)


class VmEntity(Entity):

    def __init__(self, name, cfgPath):
        Entity.__init__(self, name, cfgPath)
        self.vmxFile = ""
        self.transport = ["iso", "com.vmware.guestInfo"]

    @classmethod
    def isVM(cls):
        return True

    @classmethod
    def getRootTag(cls):
        return "vm"

    def loadRootAttributes(self, node):
        self.transport = node.getAttr("transport").split()
        return Entity.loadRootAttributes(self, node)

    def loadSection(self, node):
        if node.tag == "vmx":
            self.vmxFile = node.getAttr("file")
            if not os.path.isabs(self.vmxFile):
                self.vmxFile = os.path.join(self.dir, self.vmxFile)
                self.vmxFile = os.path.realpath(self.vmxFile)
            return True

        return Entity.loadSection(self, node)

    def writeRootAttributes(self, node):
        Entity.writeRootAttributes(self, node)
        if len(self.transport) > 0:
            node.setAttr("transport", " ".join(self.transport))

    def writeSections(self, node):
        Entity.writeSections(self, node)
        relVmxFile = CreateRelPath(self.dir, self.vmxFile)
        node.addChild(NewXmlNode("vmx").setAttr("file", relVmxFile))

    def getAllLinkNames(self):
        return [self.name]

    def startAction(self):
        self.initPowerState()

        if self.state == "Powered On":
            print("Error: Already running")
            return

        self.setupIpProperties(True)
        self.startChild()

    def startChild(self, indent=0):
        vmrun = getVmrunInstance()

        # Update OVF environment for this VM
        self.computeOvfEnvProps()

        # Create vApp environment
        vappEnv = {}
        if self.parent is None:
            vappEnv[self.name] = self.ovfEnvProps
        else:
            for c in self.parent.children:
                vappEnv[c.name] = c.ovfEnvProps

        ovfEnv = OvfEnv(self.name, vappEnv)
        vmrun.patchVmxFile(self.vmxFile, ovfEnv, self.transport)

        spc = " " * indent
        print(spc + "Starting", self.name)
        self.showOvfEnvProps(indent)

        if GetCmdOption("n", False):
            return

        vmrun.powerOn(self.vmxFile)

        # If it is a single VM, we are done
        if self.link is None:
            return

        waited = 0
        while waited < self.link.startWait:
            time.sleep(1)
            if waited % 10 == 0:
                print(spc + "Waiting for %d secs..." %
                      (self.link.startWait - waited))
            waited += 1
            if self.link.waitForTools:
                ip = vmrun.getIP(self.vmxFile)
                if len(ip) > 0:
                    print(spc + "(ip: %s)" % ip)
                    # Propagate IP up in OVF environment (dhcp policy)
                    dp = self.getDeployParams()
                    if dp.isDhcpPolicy():
                        self.propagateIp(ip)
                    return

    def stopAction(self, indent=0, force=False, silentFail=False):
        self.initPowerState()
        if self.state == "Powered Off":
            if not silentFail:
                print("Error: Already stopped")
            return

        spc = " " * indent
        if not force:
            print(spc + "Stopping", self.name)
        else:
            print(spc + "Shutting down", self.name)

        if GetCmdOption("n", False):
            return

        vmrun = getVmrunInstance()
        vmrun.powerOff(self.vmxFile, force)

        # Re-initialize power state and reset transient properties
        self.initPowerState()
        self.setupIpProperties(False)

        # Disconnect OVF iso (so VM can be exported)
        vmrun.disconnectOvfIsoInVmx(self.vmxFile, self.transport)

    def shutdownAction(self, indent=0):
        self.stopAction(indent, force=True, silentFail=True)

    def getUsedFiles(self, usedList):
        usedList.append((os.path.join(self.dir, "ovf-env.iso"), False))
        usedList.append((os.path.join(self.dir, "ovf-env.xml"), False))
        if self.isVmxInSubdir():
            usedList += OsFileList(os.path.dirname(self.vmxFile))
        Entity.getUsedFiles(self, usedList)

    def isVmxInSubdir(self):
        d1 = os.path.realpath(self.dir)
        d2 = os.path.realpath(self.vmxFile)
        return os.path.commonprefix([d1, d2]) == d1 and d2 != ""

    def initPowerState(self):
        vmrun = getVmrunInstance()
        (self.state, self.ip) = vmrun.getPowerStateAndIp(self.vmxFile)


class VAppEntity(Entity):

    def __init__(self, name, cfgPath):
        Entity.__init__(self, name, cfgPath)

    @classmethod
    def isVM(cls):
        return False

    @classmethod
    def getRootTag(cls):
        return "vapp"

    def validate(self):
        pass

    def getLinks(self):
        return self.links

    def setLinks(self, links):
        self.links = links

    def removeLink(self, name):
        if name in self.links:
            self.links.pop(name)

    def addLink(self, name, startOrder):
        link = Link(name, startOrder)
        self.links[name] = link

    def initPowerState(self):
        self.ip = ""
        self.state = "Powered Off"
        for c in self.children:
            c.initPowerState()
            if c.state == "Powered On":
                self.state = "Powered On"

    def getAllLinkNames(self):
        allLinkNames = []
        allLinkNames.append(self.name)
        for child in self.children:
            allLinkNames += child.getAllLinkNames()
        return allLinkNames

    def startAction(self):
        self.initPowerState()

        if self.state == "Powered On":
            print("Error: Already running")
            return

        self.setupIpProperties(True)
        self.startChild()

    def startChild(self, indent=0):

        self.computeOvfEnvProps()
        # An OVF environment for a VM also contains the OVF environments
        # for all siblings, so we initialize them here.
        for c in self.children:
            c.computeOvfEnvProps()

        spc = " " * indent
        print(spc + "Starting", self.name)
        self.showOvfEnvProps()

        startItems = sorted(self.children, key=lambda x: x.link.startOrder)
        for c in startItems:
            c.startChild(indent + 1)

    def stopAction(self, indent=0, force=False, silentFail=False):
        self.initPowerState()
        if self.state == "Powered Off":
            if not silentFail:
                print("Error: Already stopped")
            return

        spc = " " * indent
        if not force:
            print(spc + "Stopping", self.name)
        else:
            print(spc + "Shutting down", self.name)

        stopItems = sorted(self.children, key=lambda x: x.link.startOrder)
        stopItems.reverse()
        for c in stopItems:
            c.stopAction(indent + 1, force, silentFail=True)

        self.initPowerState()
        self.setupIpProperties(False)

    def shutdownAction(self, indent=0):
        self.stopAction(indent, force=True)


class VAppInventory(object):

    def __init__(self, path):
        self.dir = os.path.realpath(path)
        self.cfgFile = os.path.realpath(os.path.join(self.dir,
                                                     WORKSPACE_CFG_NAME))
        try:
            self.config = ReadXmlDoc(self.cfgFile)
        except Exception:
            print("Error: Cannot parse", WORKSPACE_CFG_NAME,
                  "Reason:", sys.exc_info()[1])
            sys.exit(1)

        if self.config.tag != "vapprun":
            print("Error: Invalid", WORKSPACE_CFG_NAME)
            sys.exit(1)

        cfgVersion = self.config.getAttr("configVersion", "0")
        if cfgVersion != VAPPRUN_CONFIG_VERSION:
            print("Unsupported workspace format:", cfgVersion,
                  "(supported version:", VAPPRUN_CONFIG_VERSION + ")")
            sys.exit(1)

        self.ipPool = self.config.lookup("ipPool")
        if self.ipPool is None:
            self.ipPool = NewXmlNode("ipPool")

        r, _ = self.ipPool.lookupChildTextNode("range")
        self.ipRange = CreateIpPool(r)
        self.loadInventory()

    def loadInventory(self):
        self.entities = {}
        self.roots = []
        for name in os.listdir(self.dir):
            e = self.loadEntity(name)
            if e is None:
                continue
            self.entities[name] = e
            if e.link is None:
                self.roots.append(e)

        # Setup/fixup child/parent relationships
        for name, child in self.entities.items():
            link = child.link
            if link is None:
                continue

            parentName = link.name
            if parentName in self.entities:
                parent = self.entities[parentName]
                parent.children.append(child)
                child.parent = parent
            else:
                child.unsetParent()
                child.update()  # Update on disk

    def loadEntity(self, name):
        dirname = os.path.join(self.dir, name)
        vmPath = os.path.join(dirname, VM_CFG_NAME)
        vappPath = os.path.join(dirname, VAPP_CFG_NAME)
        if os.path.exists(vmPath):
            entity = VmEntity(name, vmPath)
            entity.load()
            return entity
        elif os.path.exists(vappPath):
            entity = VAppEntity(name, vappPath)
            entity.load()
            return entity
        else:
            return None

    def updateWorkspaceConfig(self):
        node = NewXmlNode("vapprun")\
            .setAttr("configVersion", VAPPRUN_CONFIG_VERSION)\
            .addChild(self.ipPool)
        node.writeToFile(WORKSPACE_CFG_NAME)

    def initPowerState(self):
        for e in self.roots:
            e.initPowerState()

        # Power state must be initialized for this to work properly
        for e in self.entities.values():
            self.ipRange.reserve(e.getUsedIPs())


def createNewWorkspace():
    node = NewXmlNode("vapprun")\
        .setAttr("configVersion", VAPPRUN_CONFIG_VERSION)\
        .addChild(
            NewXmlNode("ipPool")
            .addXmlTextNode("netmask", "255.255.255.0")
            .addXmlTextNode("gateway", "192.168.0.1")
            .addXmlTextNode("domainName", "example.com")
            .addXmlTextNode("hostPrefix", "vapprun-")
            .addXmlTextNode("dns", "")
            .addXmlTextNode("searchPath", "")
            .addXmlTextNode("httpProxy", "")
            .addXmlTextNode("range", "192.168.0.200#8"))
    node.writeToFile(WORKSPACE_CFG_NAME)


def initializeVAppInventory():
    global vappsInstance
    wsDir = locateVAppsDirectory()
    if wsDir == "":
        vappsInstance = None
    else:
        vappsInstance = VAppInventory(wsDir)

    return vappsInstance


def getVAppsInstance():
    return vappsInstance


def locateVAppsDirectory():
    curdir = os.path.abspath(".")
    while True:
        if os.path.exists(os.path.join(curdir, WORKSPACE_CFG_NAME)):
            return curdir

        parentdir = os.path.dirname(curdir)
        if parentdir == curdir:
            return ""
        curdir = parentdir
