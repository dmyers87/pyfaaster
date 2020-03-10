# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

from enum import Enum
from typing import Union, Callable

import boto3
import simplejson as json
from pyfaaster.aws.exceptions import HTTPResponseException

lambda_client = boto3.client('lambda')


class RemoteApiError(HTTPResponseException):
    def __init__(self, feature, api, error_result):
        self.feature = feature
        self.api = api
        self.error = error_result

        super().__init__('Internal API error', statusCode=500)

    def __str__(self):
        error_type = self.error.get('errorType', 'unknown')
        error_message = self.error.get('errorMessage', 'Unknown error.')
        return f'Remote API {self.feature}.{self.api} failed with: ({error_type}) {error_message}'


def _response_error(response):
    return response.get('FunctionError')


def _encode_type(obj):
    if isinstance(obj, Enum):
        return obj.value

    raise TypeError(repr(obj) + " is not JSON serializable")


def remote_api(namespace: Union[Callable, str], feature: str, api: str):
    def remote_api_handler(handler):
        def handler_wrapper(**kwargs):
            feature_namespace = namespace(feature) if callable(namespace) else namespace

            payload = json.dumps(kwargs, default=_encode_type).encode()
            response = lambda_client.invoke(FunctionName=f'cz-{feature_namespace}-{feature}-iapi-{api}',
                                            Payload=payload)

            result_payload = response['Payload'].read().decode()
            result = json.loads(result_payload)

            if _response_error(response):
                raise RemoteApiError(feature, api, result)

            return result

        return handler_wrapper

    return remote_api_handler
