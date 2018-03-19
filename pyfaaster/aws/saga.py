# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import pyfaaster.aws.dynamo as dyn
import pyfaaster.aws.tools as tools
import pyfaaster.aws.utils as utils

logger = tools.setup_logging('pyfaaster')

NAME = 'sagas'


def init(namespace, saga):
    logger.info(f'Initializing saga')
    table = dyn.table(namespace, NAME)
    saga_key = utils.select_keys(saga, 'name')
    item = table.get_item(Key=saga_key).get('Item')
    if not item:
        current_state = saga['states'][None]['init']
        initial_item = {**saga_key, 'current_state': current_state}
        table.put_item(Item=initial_item)
        dyn.record_history(table, saga_key, 'init')
        return initial_item
    return item


def transition(namespace, saga, transition, next_state):
    logger.info(f'Transitioning {transition} to {next_state}')
    table = dyn.table(namespace, NAME)
    saga_key = utils.select_keys(saga, 'name')
    item = table.update_item(
        Key=saga_key,
        UpdateExpression='SET current_state = :next_state',
        ExpressionAttributeValues={
            ':next_state': next_state,
        },
        ReturnValues='ALL_NEW',
    )
    return dyn.record_history(table, saga_key, transition)


def skip(namespace, saga, transition):
    logger.info(f'Skipping {transition}')
    table = dyn.table(namespace, NAME)
    saga_key = utils.select_keys(saga, 'name')
    return dyn.record_history(table, saga_key, transition)
