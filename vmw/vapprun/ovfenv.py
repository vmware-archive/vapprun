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

import subprocess
from string import Template
import tempfile
import os
import sys

from .commands import mkisofsCmd
from .utils import OsTryRemove


def createOvfEnvIso(filename, content):
    imagedir = tempfile.mkdtemp()
    ovfEnvPath = os.path.join(imagedir, "ovf-env.xml")

    with open(ovfEnvPath, "w") as f:
        print(content, file=f)

    OsTryRemove(filename)
    cmd = [mkisofsCmd,
           "-r",  # don't propagate owner/permissions
           "-V", "OVF ENV",  # align label with what vsphere does
           "-quiet",
           "-rock",
           "-joliet",
           "-full-iso9660-filenames",
           "-o", filename,
           imagedir]
    try:
        subprocess.call(cmd)
    except:
        print("Error: Failed to execute mkisofs command. Is it in your path?")
        sys.exit(1)

    os.remove(ovfEnvPath)
    os.rmdir(imagedir)


def createOvfEnvDoc(vappEnv, selfId):
    header = Template('''<?xml version="1.0" encoding="UTF-8"?>
<Environment xmlns="http://schemas.dmtf.org/ovf/environment/1"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xmlns:oe="http://schemas.dmtf.org/ovf/environment/1"
             oe:id="${id}">''')
    platformSection = '''   <PlatformSection>
       <Kind>vapprun</Kind>
       <Version>1.0</Version>
       <Vendor>VMware, Inc.</Vendor>
       <Locale>en_US</Locale>
   </PlatformSection>'''
    propertyHeader = '''
   <PropertySection>'''
    propertyEntry = Template('''
      <Property oe:key="${key}" oe:value="${value}"/>''')
    propertyFooter = '''
   </PropertySection>'''
    entityHeader = Template('''
    <Entity oe:id="${id}">''')
    entityFooter = '''
    </Entity>'''
    footer = '''
    </Environment>'''

    def createPropSection(props, out):
        out.append(propertyHeader)
        for key, value in props.items():
            out.append(propertyEntry.substitute(key=key, value=value))
        out.append(propertyFooter)

    # propEnv = vappEnv[selfId]

    # String join is a very efficient way of building strings in python
    out = []
    out.append(header.substitute(id=selfId))
    out.append(platformSection)
    createPropSection(vappEnv[selfId], out)
    for id in vappEnv:
        if id != selfId:
            out.append(entityHeader.substitute(id=id))
            createPropSection(vappEnv[id], out)
            out.append(entityFooter)
    out.append(footer)

    return ''.join(out)
