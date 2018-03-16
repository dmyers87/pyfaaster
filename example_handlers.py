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
        None: {'init': 'state1'},
        'state1': {'transition1': 'state2'},
        'state2': {'transition2': 'state3',
                   'transition3': 'state4'},
    },
}


@faaster.sagas(saga=saga, transition='transition1')
def transition1(event, context, state, **kwargs):
    print(f'Saga - current_state: {state}')
    print(f'Running transition1')


@faaster.sagas(saga=saga, transition='transition2')
def transition2(event, context, state, **kwargs):
    print(f'Saga - current_state: {state}')
    print(f'Running transition2')


@faaster.sagas(saga=saga, transition='transition3')
def transition3(event, context, state, **kwargs):
    print(f'Saga - current_state: {state}')
    print(f'Running transition3')
