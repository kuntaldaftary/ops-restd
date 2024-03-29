# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import json

from jsonschema import Draft4Validator
from jsonschema import ValidationError
from jsonschema import SchemaError
from tornado.log import app_log

from opsrest.settings import settings
from opsrest.utils.utils import to_json_error
from opsrest.constants import OVSDB_SCHEMA_CONFIG
from opsrest.custom.base_controller import OP_CREATE, OP_UPDATE


class SchemaValidator():

    def __init__(self, schema_file):
        self.schema_file = settings.get(schema_file)
        try:
            json_schema = None
            with open(self.schema_file, 'r') as data_file:
                json_schema = json.load(data_file)
            self.validator = Draft4Validator(json_schema)
        except IOError as e:
            app_log.debug("Cannot read schema file: %s" % e.message)
        except SchemaError as e:
            app_log.debug("Schema error: %s" % e.message)

    def __validate_category_keys__(self, json_data):
        if OVSDB_SCHEMA_CONFIG not in json_data:
            error_json = to_json_error("Missing configuration key", None, None)
            return error_json

    def validate_json(self, json_data, operation):
        # Validate Schema
        try:
            self.validator.validate(json_data)
        except ValidationError as e:
            app_log.debug("Error: %s" % e.message)
            field = None
            if e.path:
                field = e.path[-1]
            error_json = to_json_error(e.message, None, field)
            return error_json

        # Validate required categorization keys
        if OP_CREATE == operation or OP_UPDATE == operation:
            error_json = self.__validate_category_keys__(json_data)
            return error_json

        return None
