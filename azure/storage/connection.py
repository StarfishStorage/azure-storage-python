﻿#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import os
import sys
if sys.version_info >= (3,):
    from urllib.parse import urlparse
else:
    from urlparse import urlparse
import configparser

from .constants import (
    SERVICE_HOST_BASE,
    DEFAULT_PROTOCOL,
    DEV_ACCOUNT_NAME,
    DEV_ACCOUNT_KEY,
    DEV_BLOB_HOST,
    DEV_QUEUE_HOST,
    DEV_TABLE_HOST
)
from ._error import (
    _ERROR_STORAGE_MISSING_INFO,
)

_EMULATOR_ENDPOINTS = {
   'blob': DEV_BLOB_HOST,
   'queue': DEV_QUEUE_HOST,
   'table': DEV_TABLE_HOST,
   'file': '',
}

_CONNECTION_ENDPONTS = {
    'blob': 'BlobEndpoint',
    'queue': 'QueueEndpoint',
    'table': 'TableEndpoint',
    'file': 'FileEndpoint',
}

class _ServiceParameters(object):
    def __init__(self, service, account_name=None, account_key=None, sas_token=None, 
                 is_emulated=False, protocol=DEFAULT_PROTOCOL, endpoint_suffix=SERVICE_HOST_BASE, 
                 custom_domain=None):

        self.account_name = account_name
        self.account_key = account_key
        self.sas_token = sas_token
        self.protocol = protocol or DEFAULT_PROTOCOL

        if is_emulated:
            self.account_name = DEV_ACCOUNT_NAME
            self.protocol = 'http'

            # Only set the account key if a sas_token is not present to allow sas to be used with the emulator
            self.account_key = DEV_ACCOUNT_KEY if not self.sas_token else None

            self.primary_endpoint = '{}/{}'.format(_EMULATOR_ENDPOINTS[service], self.account_name)
            self.secondary_endpoint = '{}/{}-secondary'.format(_EMULATOR_ENDPOINTS[service], self.account_name)
        else:
            # Strip whitespace from the key
            if self.account_key:
                self.account_key = self.account_key.strip()

            endpoint_suffix = endpoint_suffix or SERVICE_HOST_BASE

            # Setup the primary endpoint
            if custom_domain:
                parsed_url = urlparse(custom_domain)
                self.primary_endpoint = parsed_url.netloc + parsed_url.path
                self.protocol = self.protocol if parsed_url.scheme is '' else parsed_url.scheme
            else:
                if not self.account_name:
                    raise ValueError(_ERROR_STORAGE_MISSING_INFO)         
                self.primary_endpoint = '{}.{}.{}'.format(self.account_name, service, endpoint_suffix)
            
            # Setup the secondary endpoint
            if self.account_name:
                self.secondary_endpoint = '{}-secondary.{}.{}'.format(self.account_name, service, endpoint_suffix)
            else:
                self.secondary_endpoint = None

    def get_service_parameters(service, account_name=None, account_key=None, sas_token=None, is_emulated=None, 
                 protocol=None, endpoint_suffix=None, custom_domain=None, request_session=None, 
                 connection_string=None):
        if connection_string:
            params = _ServiceParameters._from_connection_string(connection_string, service)
        elif is_emulated:
            params = _ServiceParameters(service, is_emulated=True)
        elif account_name:
            params = _ServiceParameters(service,
                                      account_name=account_name, 
                                      account_key=account_key, 
                                      sas_token=sas_token, 
                                      is_emulated=is_emulated, 
                                      protocol=protocol, 
                                      endpoint_suffix=endpoint_suffix,
                                      custom_domain=custom_domain)
        else:
            raise ValueError(_ERROR_STORAGE_MISSING_INFO)

        params.request_session = request_session
        return params

    def _from_connection_string(connection_string, service):
        # Split into key=value pairs removing empties, then split the pairs into a dict
        config = dict(s.split('=', 1) for s in connection_string.split(';') if s)

        # Authentication
        account_name = config.get('AccountName')
        account_key = config.get('AccountKey')
        sas_token = config.get('SharedAccessSignature')

        # Emulator
        is_emulated = config.get('UseDevelopmentStorage')

        # Basic URL Configuration
        protocol = config.get('DefaultEndpointsProtocol')
        endpoint_suffix = config.get('EndpointSuffix')

        # Custom URLs
        endpoint = config.get(_CONNECTION_ENDPONTS[service])

        return _ServiceParameters(service,
                                  account_name=account_name, 
                                  account_key=account_key, 
                                  sas_token=sas_token, 
                                  is_emulated=is_emulated, 
                                  protocol=protocol, 
                                  endpoint_suffix=endpoint_suffix,
                                  custom_domain=endpoint)
