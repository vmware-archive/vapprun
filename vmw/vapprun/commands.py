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
import sys

extra_path = []

if sys.platform == "darwin":
    extra_path = ["/Library/Application Support/VMware Fusion",
                  "/Applications/VMware Fusion.app/Contents/Library"]
elif sys.platform == "win32":
    extra_path = [r"C:\Program Files (x86)\VMware\VMware VIX",
                  r"C:\Program Files (x86)\VMware\VMware Workstation",
                  r"C:\Program Files\VMware\VMware VIX",
                  r"C:\Program Files\VMware\VMware Workstation"]

for path in extra_path:
    if os.path.exists(path):
        os.environ["PATH"] = os.pathsep.join([os.environ.get("PATH", ""),
                                              path])


def _which(program):
    import os

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


mkisofsCmd = _which("mkisofs")
vmrunCmd = _which("vmrun")
vdiskmanagerCmd = _which("vmware-vdiskmanager")
