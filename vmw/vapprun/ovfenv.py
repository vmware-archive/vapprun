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
import subprocess
import sys
import tempfile
from string import Template

from .commands import MKISOFS_CMD
from .utils import OsTryRemove


class OvfEnv(object):

    def __init__(self, identifier, env):
        self._id = identifier
        self._env = env

    def create_iso(self, fname):
        imagedir = tempfile.mkdtemp()
        path = os.path.join(imagedir, "ovf-env.xml")

        with open(path, "w") as f:
            f.write(self.create_doc())

        OsTryRemove(fname)
        cmd = [MKISOFS_CMD,
               "-r",  # don't propagate owner/permissions
               "-V", "OVF ENV",  # align label with what vsphere does
               "-quiet",
               "-rock",
               "-joliet",
               "-full-iso9660-filenames",
               "-o", fname,
               imagedir]
        try:
            subprocess.call(cmd)
        except Exception:
            print("Error: Failed to execute command '%s'" % (MKISOFS_CMD))
            sys.exit(1)

        os.remove(path)
        os.rmdir(imagedir)

    def create_doc(self):
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
</Environment>
'''

        def createPropSection(props, out):
            out.append(propertyHeader)
            for key, value in props.items():
                out.append(propertyEntry.substitute(key=key, value=value))
            out.append(propertyFooter)

        # propEnv = vappEnv[selfId]

        # String join is a very efficient way of building strings in python
        out = []
        out.append(header.substitute(id=self._id))
        out.append(platformSection)
        createPropSection(self._env[self._id], out)
        for _id in self._env:
            if _id != self._id:
                out.append(entityHeader.substitute(id=_id))
                createPropSection(self._env[_id], out)
                out.append(entityFooter)
        out.append(footer)

        return ''.join(out)
