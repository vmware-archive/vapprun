#!/usr/bin/env bats
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

# Commands to cover
# create-vapp       -- OK
# create-vm         -- OK
# def-property      -- OK
# delete            -- OK
# edit              
# fsck              
# help              
# init              -- OK
# link-vm           
# list              -- OK
# set-property      -- OK
# shutdown          
# start             
# stop              
# workspace         -- OK

load common

setup() {
    init_workspace
}

teardown() {
    delete_workspace
}

# Workspace tests

@test "Check workspace" {
    [ -d "$VAPPRUN_WORKSPACE" ]
}

@test "Check workspace init" {
    [ -e "$VAPPRUN_WORKSPACE"/vapprun.cfg ]
}

@test "Check empty workspace" {
    "$VAPPRUN" workspace
    run "$VAPPRUN" list
    [[ ${lines[0]} = "Empty workspace" ]]
}

# VM tests

@test "Check vm creation" {
    run create_vm foo
    [ -e "$VAPPRUN_WORKSPACE"/foo/vm.cfg -a \
         -e "$VAPPRUN_WORKSPACE"/foo/vmx/vm.vmx -a \
         -e "$VAPPRUN_WORKSPACE"/foo/vmx/disk.vmdk ]
}

@test "Check vm in list" {
    create_vm foo
    "$VAPPRUN" list -q | tail -1 | {
            run awk '{print $1, $2}'
            [[ ${lines[0]} = "foo VM" ]]
        }
}

@test "Check vm properties" {
    create_vm foo
    run "$VAPPRUN" list -q foo
}

@test "Check vm property def" {
    KEY=plop
    TYPE=ip:Network

    create_vm foo
    run "$VAPPRUN" def-property foo key="$KEY" type="$TYPE"
}

@test "Check vm property set" {
    KEY=plop
    TYPE=ip:Network
    VALUE=0.0.0.0

    create_vm foo
    "$VAPPRUN" def-property foo key="$KEY" type="$TYPE"
    "$VAPPRUN" set-property foo "$KEY=$VALUE"
    "$VAPPRUN" list -q foo
    "$VAPPRUN" list -q foo | grep "$KEY" | {
            run awk '{print $1, $2, $3}'
            [[ ${lines[0]} =~ "$KEY $TYPE True" ]]
            [[ ${lines[1]} =~ "$KEY $VALUE" ]]
            [[ ${lines[2]} =~ "$KEY $VALUE" ]]
        }
    
}

@test "Check vm delete" {
    create_vm foo
    delete_vm foo
    run "$VAPPRUN" list
    [[ ${lines[0]} = "Empty workspace" ]]
}

# vApp tests

@test "Check vapp creation" {
    run create_vapp foo
    [ -e "$VAPPRUN_WORKSPACE"/foo/vapp.cfg ]
}

@test "Check vapp in list" {
    create_vapp foo
    "$VAPPRUN" list -q | tail -1 | {
            run awk '{print $1, $2}'
            [[ ${lines[0]} = "foo vApp" ]]
        }
}

@test "Check vapp properties" {
    create_vapp foo
    run "$VAPPRUN" list -q foo
}

@test "Check vapp property set" {
    KEY=plop
    TYPE=ip:Network
    VALUE=0.0.0.0

    create_vapp foo
    "$VAPPRUN" def-property foo key="$KEY" type="$TYPE"
    "$VAPPRUN" set-property foo "$KEY=$VALUE"
    "$VAPPRUN" list -q foo
    "$VAPPRUN" list -q foo | grep "$KEY" | {
            run awk '{print $1, $2, $3}'
            [[ ${lines[0]} =~ "$KEY $TYPE True" ]]
            [[ ${lines[1]} =~ "$KEY $VALUE" ]]
        }
    
}

@test "Check vapp delete" {
    create_vapp foo
    delete_vapp foo
    run "$VAPPRUN" list
    [[ ${lines[0]} = "Empty workspace" ]]
}
