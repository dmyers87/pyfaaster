# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import datetime as dt
import os

import boto3
import boto3.dynamodb.conditions as dynamo_conditions

import pyfaaster.aws.tools as tools

logger = tools.setup_logging('pyfaaster')


def table(namespace, name):
    """Return a boto3 DynamoDB.Table for the given namespace and name. This method
    will create a 'standard' CZ Core table name from the namespace and name.
    Setting the DYNAMODB_ENDPOINTURL environment variable will override the
    default boto3 behaviour (mostly for testing).

    Args:
        namespace (str): unique identitifier of this core deployment
        name (str): the base name of the table

    Returns:
        table (Table): boto3 DynamoDB.Table
    """
    name = f'pyfaaster-example-{namespace}-{name}'
    dynamodb_endpointurl = os.environ.get('DYNAMODB_ENDPOINTURL')
    if dynamodb_endpointurl:
        logger.debug(f'Connecting to {name} table at {dynamodb_endpointurl}')
        return boto3.resource('dynamodb', endpoint_url=dynamodb_endpointurl).Table(name)
    else:
        logger.debug(f'Connecting to {name} table using default endpoint')
        return boto3.resource('dynamodb').Table(name)


def record_history(table, key, value):
    logger.debug(f'Recording history for {key}')
    [[k, v]] = key.items()
    now = dt.datetime.now(tz=dt.timezone.utc).isoformat()
    return add_to_set(table, 'history', k, v, f'{now}|{value}')


def add_to_set(table, set_attribute, key_name, key_value, value):
    """
    For a given item, atomically add a value to the indicated stringset

    Args:
        table (Table): The dynamodb table resource to use
        set_attribute (str): The name of the stringset attribute that will be modified
        key_name (str):  The name of the partition key of the Item whose data is to be modified
        key_value (str):  The value of the partition key of the Item whose data is to be modified
        value (str): A value to add to the given stringset

    Returns:
        dict - a copy of the item data post-modification
    """
    logger.debug(f'Adding value {value} to the {set_attribute} '
                 f'attribute of item {key_name}={key_value} in {table.name}')
    try:
        item = table.update_item(
            Key={key_name: key_value},
            ConditionExpression='#key_name = :key_value',
            UpdateExpression=f'ADD {set_attribute} :value',
            ExpressionAttributeValues={
                ':value': {value},
                ':key_value': key_value,
            },
            ExpressionAttributeNames={
                '#key_name': key_name,
            },
            ReturnValues='ALL_NEW'
        )
        return item['Attributes'] if item else None
    except Exception as err:
        message = (f'Failed to add value {value} to the {set_attribute} '
                   f'attribute of item {key_name}={key_value} in {table.name}')
        logger.warning(message)
        logger.exception(err)
        return None


def remove_from_set(table, set_attribute, key_name, key_value, value):
    """
    For a given item, atomically remove a value from the indicated stringset

    Args:
        table (Table): The dynamodb table resource to use
        set_attribute (str): The name of the stringset attribute that will be modified
        key_name (str):  The name of the partition key of the Item whose data is to be modified
        key_value (str):  The value of the partition key of the Item whose data is to be modified
        value (str): A value to add to the given stringset

    Returns:
        dict - a copy of the item data post-modification
    """
    logger.debug(f'Removing value {value} from the {set_attribute} '
                 f'attribute of item {key_name}={key_value} in {table.name}')
    try:
        item = table.update_item(
            Key={key_name: key_value},
            ConditionExpression=f'{key_name} = :key',
            UpdateExpression=f'DELETE {set_attribute} :value',
            ExpressionAttributeValues={
                ':value': {value},
                ':key': key_value
            },
            ReturnValues='ALL_NEW'
        )
        return item['Attributes'] if item else None
    except Exception as err:
        message = (f'Failed to remove value {value} from the {set_attribute} '
                   f'attribute of item {key_name}={key_value} in {table.name}')
        logger.warning(message)
        logger.exception(err)
        return None


def set_swap(table, set_source, set_target, key_name, key_value, value):
    """
    For a given item, atomically move one of its set values between stringsets

    Args:
        table (Table): The dynamodb table resource to use
        set_source (str): The name of the stringset attribute that will be the source of the swap
        set_target (str): The name of the stringset attribute that will be the target of the swap
        key_name (str):  The name of the partition key of the Item whose data is to be modified
        key_value (str):  The value of the partition key of the Item whose data is to be modified
        value (str): A value to move between sets

    Returns:
        dict - a copy of the item data post-modification
    """
    logger.info(f'Moving value {value} from the {set_source} '
                f'attribute to the {set_target} attribute of item {key_name}={key_value} in {table.name}')
    try:
        item = table.update_item(
            Key={key_name: key_value},
            ConditionExpression=f'{key_name} = :key',
            UpdateExpression=f'DELETE {set_source} :value ADD {set_target} :value',
            ExpressionAttributeValues={
                ':value': {value},
                ':key': key_value
            },
            ReturnValues='ALL_NEW'
        )
        return item['Attributes'] if item else None
    except Exception as err:
        message = (f'Failed to move value {value} from the {set_source} '
                   f'attribute to the {set_target} attribute of item {key_name}={key_value} in {table.name}')
        logger.warning(message)
        logger.exception(err)
        return None


def add_to_list(table, list_attribute, key_name, key_value, value):
    """
    For a given item, atomically add a value to the indicated list attribute.

    Args:
        table (Table): The dynamodb table resource to use
        list_attribute (str): The name of the list attribute that will be modified
        key_name (str):  The name of the partition key of the Item whose data is to be modified
        key_value (str):  The value of the partition key of the Item whose data is to be modified
        value: A value to add to the given list.  Can be any type supported by dynamodb

    Returns:
        dict - a copy of the item data post-modification
    """
    logger.debug(f'Adding value {value} to the {list_attribute} '
                 f'attribute of item {key_name}={key_value} in {table.name}')
    try:
        expression = f'SET {list_attribute} = list_append(if_not_exists({list_attribute}, :empty_list), :value)'
        item = table.update_item(
            Key={key_name: key_value},
            ConditionExpression=f'{key_name} = :key',
            UpdateExpression=expression,
            ExpressionAttributeValues={
                ':value': [value],
                ':empty_list': [],
                ':key': key_value
            },
            ReturnValues='ALL_NEW'
        )
        return item['Attributes'] if item else None
    except Exception as err:
        message = (f'Failed to add value {value} to the {list_attribute} '
                   f'attribute of item {key_name}={key_value} in {table.name}')
        logger.warning(message)
        logger.exception(err)
        return None


def list_swap(table, list_source, source_list_index, list_target, key_name, key_value, value):
    """
    For a given item, atomically move one of its values between lists

    Args:
        table (Table): The dynamodb table resource to use
        list_source (str): The name of the list attribute that will be the source of the swap
        source_list_index (int): The index of the desired item's position in the source list.
        list_target (str): The name of the list attribute that will be the target of the swap
        key_name (str):  The name of the partition key of the Item whose data is to be modified
        key_value (str):  The value of the partition key of the Item whose data is to be modified
        value: A value to move between lists.  Can be any type supported by dynamodb

    Returns:
        dict - a copy of the item data post-modification
    """
    logger.info(f'Moving value {value} from the {list_source} '
                f'attribute to the {list_target} attribute of item {key_name}={key_value} in {table.name}')
    try:
        expression = f'REMOVE {list_source}[{source_list_index}]'
        table.update_item(
            Key={key_name: key_value},
            ConditionExpression=f'{key_name} = :key',
            UpdateExpression=expression,
            ExpressionAttributeValues={
                ':key': key_value,
            },
            ReturnValues='ALL_NEW'
        )
        expression = f'SET {list_target} = list_append(if_not_exists({list_target}, :empty_list), :value)'
        item = table.update_item(
            Key={key_name: key_value},
            ConditionExpression=f'{key_name} = :key',
            UpdateExpression=expression,
            ExpressionAttributeValues={
                ':key': key_value,
                ':value': [value],
                ':empty_list': []
            },
            ReturnValues='ALL_NEW'
        )
        return item['Attributes'] if item else None
    except Exception as err:
        message = (f'Failed to move value {value} from the {list_source} '
                   f'attribute to the {list_target} attribute of item {key_name}={key_value} in {table.name}')
        logger.warning(message)
        logger.exception(err)
        return None


def query_index_and_ensure_unique(table, index_name, attribute_name, attribute_value):
    """
    Query a Global Secondary Index and ensure the result is unique and non-empty.
    Logs exceptional conditions, but does not raise exceptions - it leaves this up to the caller.

    Args:
        table (Table): The dynamodb table resource to use
        index_name: The name of the index to query
        attribute_name: (str) - The name of the attribute to search
        attribute_value: (str) -The value of the attribute to search

    Returns:
        The desired unique item from the index (dict) or None if the index does not contain the item.
    """
    result = table.query(IndexName=index_name,
                         Select='ALL_ATTRIBUTES',
                         KeyConditionExpression=dynamo_conditions.Key(attribute_name).eq(attribute_value))

    if result['Count'] == 0:
        logger.info(f'there are no records for {attribute_name}: {attribute_value}')
    elif result['Count'] > 1:
        logger.warning(f'there are multiple records for {attribute_name}: {attribute_value}. this should not happen')
    else:
        return result['Items'][0]
    return None
