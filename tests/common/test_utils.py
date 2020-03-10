# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

"""
Unit tests for various general utility functions that don't have any connection to domain/business logic
"""

import os
import attrdict
import enum
import pytest
import simplejson as json

import pyfaaster.common.utils as utils


@pytest.mark.unit
def test_deep_get_exact_match():
    input_dict = {
        'foo': {
            '123': 'abc',
            '456': 'def'
        },
        'bar': {
            '789': 'ghi',
            '012': 'jkl'
        },
        'baz': {
            '345': 'mno',
            '678': 'pqr'
        }
    }
    result = utils.deep_get(input_dict, 'baz', '345')
    assert 'mno' == result
    result = utils.deep_get(input_dict, 'foo')
    assert {'123': 'abc', '456': 'def'} == result
    result = utils.deep_get(input_dict, 'BaR', '012')
    assert result is None


@pytest.mark.unit
def test_deep_get_case_insensitive_match():
    input_dict = {
        'foo': {
            '123': 'abc',
            '456': 'def',
            'AAA': {
                'BBB': '919'
            }
        },
        'bar': {
            '789': 'ghi',
            '012': 'jkl'
        },
        'bAz': {
            '345': 'mno',
            '678': 'pqr'
        }
    }
    result = utils.deep_get(input_dict, 'BaR', '012', ignore_case=True)
    assert 'jkl' == result
    result = utils.deep_get(input_dict, 'bar', '012', ignore_case=True)
    assert 'jkl' == result
    result = utils.deep_get(input_dict, 'baz', '345', ignore_case=True)
    assert 'mno' == result
    result = utils.deep_get(input_dict, 'FOO', 'aAa', 'BbB', ignore_case=True)
    assert '919' == result
    result = utils.deep_get(input_dict, 'BaR', '012', ignore_case=False)
    assert result is None
    result = utils.deep_get(input_dict, 'bar', '012', ignore_case=False)
    assert 'jkl' == result


@pytest.mark.unit
def test_deep_get_case_mixed_keys():
    input_dict = {
        frozenset({1, 2, 3}): {
            123: 'abc',
            456.9: 'def'
        },
        123: {
            (3, 4): 'ghi',
            (5, 6): 'jkl'
        },
        (1, 2): {
            '345': 'mno',
            '678': 'pqr'
        }
    }
    result = utils.deep_get(input_dict, 123, (5, 6), ignore_case=True)
    assert 'jkl' == result
    result = utils.deep_get(input_dict, (1, 2), '678', ignore_case=False)
    assert 'pqr' == result
    result = utils.deep_get(input_dict, frozenset({1, 2, 3}), 456.9)
    assert 'def' == result


@pytest.mark.unit
def test_deep_get_bad_input():
    result = utils.deep_get(None, 'foo', '012')
    assert result is None
    result = utils.deep_get([], 'foo', '012')
    assert result is None


@pytest.mark.unit
def test_deep_get_identity_input():
    result = utils.deep_get({'foo': 'bar'})
    assert result == {'foo': 'bar'}


@pytest.mark.unit
def test_deep_get_no_match():
    input_dict = {
        'foo': {
            '123': 'abc',
            '456': 'def'
        },
        'bar': {
            '789': 'ghi',
            '012': 'jkl'
        },
        'baz': {
            '345': 'mno',
            '678': 'pqr'
        }
    }
    result = utils.deep_get(input_dict, 'bar', 'aaa')
    assert result is None
    result = utils.deep_get(input_dict, 'foobar')
    assert result is None
    result = utils.deep_get(input_dict, None)
    assert result is None


@pytest.mark.unit
def test_select_keys_one():
    input_dict = {
        'a': 1,
        'b': 2,
        'c': 3,
    }
    result = utils.select_keys(input_dict, 'a')
    assert result['a'] == input_dict['a']
    assert 'b' not in result and 'c' not in result


@pytest.mark.unit
def test_select_keys_all():
    input_dict = {
        'a': 1,
        'b': 2,
        'c': 3,
    }
    result = utils.select_keys(input_dict, *input_dict.keys())
    assert result == input_dict


@pytest.mark.unit
def test_select_keys_missing():
    input_dict = {
        'a': 1,
        'b': 2,
        'c': 3,
    }
    result = utils.select_keys(input_dict, *(list(input_dict.keys()) + ['bad_key']))
    assert result == input_dict


@pytest.mark.unit
def test_select_keys_none():
    assert utils.select_keys({}) == {}
    assert utils.select_keys({'a': 1}) == {}
    assert utils.select_keys(None, 'a') is None


@pytest.mark.unit
def test_enum_json_encoder():
    class SampleEnum(enum.Enum):
        NOT_OK = 0
        OK = 1
        MAYBE_OK = 2

    payload = {'key': SampleEnum.OK}
    result = json.dumps(payload, cls=utils.EnumEncoder)
    assert result
    result = json.loads(result)
    assert result['key'] == SampleEnum.OK.value


@pytest.mark.unit
def test_group_by():
    xs = [['a', 1], ['b', 2], ['c', 3], ['a', 2]]
    assert utils.group_by(xs, lambda x: x[0]) == {'a': [['a', 1], ['a', 2]], 'b': [['b', 2]], 'c': [['c', 3]]}
    assert utils.group_by(xs, lambda x: x[0], fys=lambda ys: [y[1] for y in ys]) == {'a': [1, 2], 'b': [2], 'c': [3]}


class Context:
    def __init__(self, mocker, module_under_test, modules_to_mock=()):
        self._mocker = mocker
        self._orig_env = os.environ.copy()
        self._module_under_test = module_under_test
        self._modules_to_mock = modules_to_mock

    def __enter__(self):
        context = attrdict.AttrMap()
        context.prefix = self._module_under_test.__name__
        for m in self._modules_to_mock:
            context[f'mock_{m}'] = self._mocker.patch(f'{context.prefix}.{m}')

        context.os = {'environ': os.environ}
        context.mocker = self._mocker
        return context

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._mocker.stopall()
        os.environ = self._orig_env


class MockEx:
    def __init__(self, mock):
        self._mock = mock

    def if_called_with(self, *expected_args, **expected_kwargs):
        icw = _IfCalledWith(*expected_args, **expected_kwargs)
        self._mock.side_effect = icw
        return icw

    def was_called_with(self, *expected_args, **expected_kwargs):
        return _MockCall(self._mock, 1).was_called_with(*expected_args, **expected_kwargs)

    def call(self, num):
        return _MockCall(self._mock, num)


class _MockCall:
    def __init__(self, mock, call_num):
        self._mock = mock
        self._call_num = call_num

    def was_called_with(self, *expected_args, **expected_kwargs):
        args, kwargs = _extract_call_elements(self._mock, self._call_num)
        return args == expected_args and kwargs == expected_kwargs


class _IfCalledWith:
    def __init__(self, *expected_args, **expected_kwargs):
        self._expected_args = expected_args
        self._expected_kwargs = expected_kwargs
        self._return_value = None

    def return_value(self, value):
        self._return_value = value
        return self

    def __call__(self, *args, **kwargs):
        if self._expected_args == args and self._expected_kwargs == kwargs:
            return self._return_value


def _extract_call_elements(mock, call_number=1):
    if mock is None or mock.call_count == 0:
        raise TypeError('Mock must have calls')
    if call_number > len(mock.mock_calls) or call_number < 1:
        raise TypeError(f'Invalid call number, should be between 1 and {len(mock.mock_calls)}, inclusive')
    _, args, kwargs = mock.mock_calls[call_number - 1]
    return args, kwargs
