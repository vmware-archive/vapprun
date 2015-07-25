#!/usr/bin/env bash
#
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

export VAPPRUN="$PWD/vapprun"

create_workspace() {
    export VAPPRUN_WORKSPACE=$(mktemp -d -p $BATS_TMPDIR)
    cd "$VAPPRUN_WORKSPACE"
}

init_workspace() {
    create_workspace
    "$VAPPRUN" init
}

delete_workspace() {
    rm -rf "$VAPPRUN_WORKSPACE"
}

create_vm() {
    "$VAPPRUN" create-vm "$1" 2>/dev/null
}

delete_vm() {
    "$VAPPRUN" delete "$1"
}

create_vapp() {
    "$VAPPRUN" create-vapp "$1"
}

delete_vapp() {
    "$VAPPRUN" delete "$1"
}
