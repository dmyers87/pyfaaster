# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import pyfaaster.aws.handlers_decorators as faaster


@faaster.default()
def hello_world(event, context, **kwargs):
    return {
        'statusCode': 200,
        'body': 'Hello, World!'
    }


saga = {
    'name': 'example-saga',
    'states': {
        None:                       {'init':     'unknown'},
        'unknown':                  {'register': 'waiting_for_invite',
                                     'invite':   'waiting_for_registration',},
        'waiting_for_invite':       {'invite':   'member'},
        'waiting_for_registration': {'register': 'member'},
        'member': None
    },
}


@faaster.sagas(saga=saga, transition='register')
def register(event, context, state, **kwargs):
    print(f'Saga - current_state: {state}')
    print(f'Registering')


@faaster.sagas(saga=saga, transition='invite')
def invite(event, context, state, **kwargs):
    print(f'Saga - current_state: {state}')
    print(f'Inviting')
