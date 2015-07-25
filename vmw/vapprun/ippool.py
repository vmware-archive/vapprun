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

"""ippool handles pool of IP addresses for vApp"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import re


class IpPool(object):

    def __init__(self, ipSet):
        self.ipSet = ipSet
        self.reserved = []

    def allocate(self):
        if len(self.ipSet) == 0:
            return None
        return self.ipSet.pop()

    def reserve(self, reserveSet):
        self.reserved += reserveSet.union(self.ipSet)
        self.ipSet = self.ipSet.difference(reserveSet)

    def unreserve(self, ip):
        if ip in self.reserved:
            self.ipSet.add(ip)
            self.reserved.remove(ip)


def CreateIpPool(ipPoolSpec):
    def nextIp(ipIn):
        ipOut = list(ipIn)
        ipOut[3] = ipOut[3] + 1
        pos = 3
        while pos >= 0 and ipOut[pos] > 255:
            ipOut[pos] = 0
            ipOut[pos - 1] = ip[pos - 1] + 1
            pos = pos - 1
        if ipOut[0] > 255:
            return ipIn
        return ipOut

    if len(ipPoolSpec) == 0:
        return IpPool(set())

    patt = re.compile(
        r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})#(\d{1,3})$")
    m = patt.match(ipPoolSpec)
    if m is None:
        return None

    ip = [int(m.group(i)) for i in range(1, 5)]
    count = int(m.group(5))
    ipSet = set()
    for i in range(0, count):
        ipSet.add(".".join([str(item) for item in ip]))
        ip = nextIp(ip)

    return IpPool(ipSet)
