# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.
import json
from enum import Enum

import pytest
from attrdict import AttrDict
from mock import ANY

from pyfaaster.aws import internal_api_decorators as decorators
from tests.common.test_utils import Context, MockEx

TEST_NAMESPACE = 'fake-namespace'
TEST_REMOTE_FEATURE = 'fake-feature'
TEST_REMOTE_API_FUNCTION = 'fake-api-func'


@pytest.fixture(scope='function')
def context(mocker):
    with Context(mocker, decorators, ['lambda_client']) as context:
        MockEx(context.mock_lambda_client.invoke).if_called_with(
            FunctionName=ANY, Payload=ANY).return_value(_get_lambda_response())
        yield context


@decorators.remote_api('fake-namespace', 'fake-feature', 'fake-api')
def _fake_remote_api(arg1=None, arg2=None):
    pass


@pytest.mark.unit
def test_remote_api_should_invoke_lambda(context):
    _fake_remote_api()

    assert MockEx(context.mock_lambda_client.invoke).was_called_with(FunctionName=ANY, Payload=ANY)


@pytest.mark.unit
@pytest.mark.parametrize('namespace,feature,api,expected_lambda', [
    ('NS1', 'some-feature', 'test-function', 'cz-NS1-some-feature-iapi-test-function'),
    ('matt', 'better-feature', 'test-function2', 'cz-matt-better-feature-iapi-test-function2')
])
def test_remote_api_should_invoke_correct_lambda_function(context, namespace, feature, api, expected_lambda):
    @decorators.remote_api(namespace, feature, api)
    def remote_api_func():
        pass

    remote_api_func()

    assert MockEx(context.mock_lambda_client.invoke).was_called_with(
        FunctionName=expected_lambda, Payload=ANY)


class TestEnum(Enum):
    One = 'one'
    Two = 'two'


@pytest.mark.unit
@pytest.mark.parametrize('arg1,arg2,expected_payload', [
    ('some-arg', 1, '{"arg1": "some-arg", "arg2": 1}'),
    ('other-arg', True, '{"arg1": "other-arg", "arg2": true}'),
    (123, TestEnum.One, '{"arg1": 123, "arg2": "one"}'),
])
def test_remote_api_should_invoke_lambda_with_correct_payload(context, arg1, arg2, expected_payload):
    _fake_remote_api(arg1=arg1, arg2=arg2)

    assert MockEx(context.mock_lambda_client.invoke).was_called_with(
        FunctionName=ANY, Payload=expected_payload.encode())


@pytest.mark.unit
@pytest.mark.parametrize('expected_result', [
    {'result': [1, 2, 3]},
    {'status': 'good'}
])
def test_remote_api_should_return_result_from_lambda(context, expected_result):
    MockEx(context.mock_lambda_client.invoke).if_called_with(
        FunctionName=ANY, Payload=ANY).return_value(_get_lambda_response(result=expected_result))

    result = _fake_remote_api()

    assert result == expected_result


@pytest.mark.unit
@pytest.mark.parametrize('feature,api,error_message,error_type,result', [
    ('some-feature', 'test-function', 'got an error', 'SomeError', {'other': 'data'}),
    ('better-feature', 'test-function2', 'yet another error', 'ThisIsBad', {}),
    ('better-feature', 'test-function2', None, 'ThisIsBad', {}),
    ('better-feature', 'test-function2', None, None, {}),
])
def test_remote_api_should_handle_errors_from_lambda(context, feature, api, error_message, error_type, result):
    error_result = {
        **({'errorType': error_type} if error_type else {}),
        **({'errorMessage': error_message} if error_message else {}),
        **result
    }

    MockEx(context.mock_lambda_client.invoke).if_called_with(
        FunctionName=ANY, Payload=ANY).return_value(_get_lambda_response(is_error=True, result=error_result))

    @decorators.remote_api('ns', feature, api)
    def remote_api_func():
        pass

    with pytest.raises(decorators.RemoteApiError) as error:
        remote_api_func()

    exception = error.value
    assert exception.feature == feature
    assert exception.api == api
    assert exception.error == error_result
    assert f'{feature}.{api}' in str(exception)
    assert (error_message or 'Unknown error') in str(exception)
    assert (error_type or 'unknown') in str(exception)


def _get_lambda_response(is_error=False, result=None):
    return {
        "StatusCode": 200,
        **({"FunctionError": "Unhandled"} if is_error else {}),
        "ExecutedVersion": "$LATEST",
        "Payload": AttrDict({
            'read': lambda: json.dumps(result or {}).encode()
        })
    }
