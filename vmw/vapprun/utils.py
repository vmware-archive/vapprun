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
import ConfigParser
import xml.dom.minidom

options = {}


def GetCmdOption(name, default):
    global options
    if name not in options:
        return default
    return options[name]


def SetCmdOption(name, value):
    global options
    options[name] = value


def StrToBool(s, defaultValue=False):
    s = str(s)
    if len(s) == 0:
        return defaultValue
    return s.lower() in ["true", "1", "yes"]


def BoolToStr(b):
    if b:
        return "true"
    else:
        return "false"


def OsTryRemove(file):
    try:
        os.remove(file)
    except:
        pass


def OsTryRmdir(dir):
    try:
        os.rmdir(dir)
    except:
        pass


def OsMkdirs(newdir):
    if os.path.isdir(newdir):
        return []
    elif os.path.isfile(newdir):
        raise OSError("Cannot create directory %s" % newdir)
    else:
        res = []
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            res += OsMkdirs(head)
        if tail:
            os.mkdir(newdir)
            res.append(newdir)
        return res


# List of tuples (name, isDir)
def OsFileList(dir):
    list = []
    for root, dirs, files in os.walk(top=dir, topdown=False, onerror=None):
        for f in files:
            path = os.path.realpath(os.path.join(root, f))
            list.append((path, False))
        list.append((os.path.realpath(root), True))
    return list


def OsFileListRemove(list):
    for name, isDir in list:
        if isDir:
            OsTryRmdir(name)
        else:
            OsTryRemove(name)


def CreateRelPath(baseDir, dir):
    d1 = os.path.realpath(baseDir)
    d2 = os.path.realpath(dir)
    if os.path.commonprefix([d1, d2]) == d1 and d2 != "":
        relDir = dir[len(d1):]
        while(len(relDir) > 0 and relDir[0] in "\//"):
            relDir = relDir[1:]
        return relDir
    return d2


def WriteTxtFile(file, content):
    OsTryRemove(file)
    with open(file, "wt") as f:
        print(content, file=f)


class MyConfigParser(ConfigParser.ConfigParser):

    def get(self, section, key, default=""):
        try:
            return ConfigParser.ConfigParser.get(self, section, key)
        except ConfigParser.NoOptionError:
            return default
        except ConfigParser.NoSectionError:
            return default

    def getint(self, section, key, default=0):
        try:
            return ConfigParser.ConfigParser.getint(self, section, key)
        except:
            return default


class XmlNode:
    def __init__(self, tag, attrs={}, value=None, children=[]):
        self.tag = tag
        self.attrs = attrs
        self.value = value
        self.children = children

    def list(self, tag):
        return filter(lambda p: p.tag == tag, self.children)

    def lookup(self, tag):
        for c in self.children:
            if c.tag == tag:
                return c
        return None

    def lookupChildTextNode(self, tag):
        for c in self.children:
            if c.tag == tag and c.value is not None:
                return (c.value.strip(), True)
        return ("", False)

    def updateChildTextNode(self, tag, val):
        for c in self.children:
            if c.tag == tag:
                c.value = str(val).strip()
                return

    def toXmlDom(self):
        impl = xml.dom.minidom.getDOMImplementation()
        doc = impl.createDocument(None, self.tag, None)
        root = doc.documentElement
        self.toXmlDomHelper(doc, root)
        return doc

    def toXmlDomHelper(self, doc, elem):
        for key, value in self.attrs.items():
            elem.setAttribute(key, str(value))

        if self.value is not None:
            tn = doc.createTextNode(str(self.value).strip())
            elem.appendChild(tn)

        for cn in self.children:
            en = doc.createElement(cn.tag)
            cn.toXmlDomHelper(doc, en)
            elem.appendChild(en)

    def writeToFile(self, name):
        doc = self.toXmlDom()
        f = open(name, "w")
        doc.writexml(writer=f, addindent="  ", newl="\n")
        doc.unlink()
        f.close()

    def setAttr(self, key, value):
        self.attrs[key] = value
        return self

    def getAttr(self, key, value=""):
        if key in self.attrs:
            return self.attrs[key]
        else:
            return value

    def getAttrInt(self, key, value):
        try:
            return int(self.getAttr(key, value))
        except:
            return value

    def getAttrBool(self, key, value):
        try:
            return StrToBool(self.getAttr(key, value).lower())
        except:
            return value

    def addChild(self, n):
        self.children.append(n)
        return self

    def addXmlNode(self, tag):
        self.children.append(NewXmlNode(tag))
        return self

    def addXmlTextNode(self, tag, text):
        self.children.append(NewXmlTextNode(tag, text))
        return self

    def dump(self, indent=""):
        print(indent, self.tag, self.attrs, self.value)
        for c in self.children:
            c.dump(indent + "  ")


def NewXmlNode(tag):
    return XmlNode(tag, attrs=dict(), children=[])


def NewXmlTextNode(tag, value):
    return XmlNode(tag, attrs=dict(), children=[], value=value)


def ReadXmlDoc(filename):
    try:
        doc = xml.dom.minidom.parse(filename)
        node = ReadXmlElement(doc.documentElement)
        doc.unlink()
    except IOError:
        return None
    return node


def ReadXmlElement(elem):
    attrs = {}
    children = []
    value = None

    for i in range(0, elem.attributes.length):
        a = elem.attributes.item(i)
        attrs[a.name] = a.value

    for c in elem.childNodes:
        if c.nodeType == elem.ELEMENT_NODE:
            children.append(ReadXmlElement(c))
        elif c.nodeType == elem.TEXT_NODE:
            value = c.data

    return XmlNode(elem.tagName, attrs, value, children)