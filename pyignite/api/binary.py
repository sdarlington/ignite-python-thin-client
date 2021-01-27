# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Union

from pyignite.constants import *
from pyignite.datatypes.binary import (
    body_struct, enum_struct, schema_struct, binary_fields_struct,
)
from pyignite.datatypes import String, Int, Bool
from pyignite.queries import Query
from pyignite.queries.op_codes import *
from pyignite.utils import int_overflow, entity_id
from .result import APIResult
from ..queries.response import Response


def get_binary_type(
    connection: 'Connection', binary_type: Union[str, int], query_id=None,
) -> APIResult:
    """
    Gets the binary type information by type ID.

    :param connection: connection to Ignite server,
    :param binary_type: binary type name or ID,
    :param query_id: (optional) a value generated by client and returned as-is
     in response.query_id. When the parameter is omitted, a random value
     is generated,
    :return: API result data object.
    """

    query_struct = Query(
        OP_GET_BINARY_TYPE,
        [
            ('type_id', Int),
        ],
        query_id=query_id,
    )

    _, send_buffer = query_struct.from_python({
        'type_id': entity_id(binary_type),
    })
    connection.send(send_buffer)

    response_head_struct = Response(protocol_version=connection.get_protocol_version(),
                                    following=[('type_exists', Bool)])

    response_head_type, recv_buffer = response_head_struct.parse(connection)
    response_head = response_head_type.from_buffer_copy(recv_buffer)
    response_parts = []
    if response_head.type_exists:
        resp_body_type, resp_body_buffer = body_struct.parse(connection)
        response_parts.append(('body', resp_body_type))
        resp_body = resp_body_type.from_buffer_copy(resp_body_buffer)
        recv_buffer += resp_body_buffer
        if resp_body.is_enum:
            resp_enum, resp_enum_buffer = enum_struct.parse(connection)
            response_parts.append(('enums', resp_enum))
            recv_buffer += resp_enum_buffer
        resp_schema_type, resp_schema_buffer = schema_struct.parse(connection)
        response_parts.append(('schema', resp_schema_type))
        recv_buffer += resp_schema_buffer

    response_class = type(
        'GetBinaryTypeResponse',
        (response_head_type,),
        {
            '_pack_': 1,
            '_fields_': response_parts,
        }
    )
    response = response_class.from_buffer_copy(recv_buffer)
    result = APIResult(response)
    if result.status != 0:
        return result
    result.value = {
        'type_exists': response.type_exists
    }
    if hasattr(response, 'body'):
        result.value.update(body_struct.to_python(response.body))
    if hasattr(response, 'enums'):
        result.value['enums'] = enum_struct.to_python(response.enums)
    if hasattr(response, 'schema'):
        result.value['schema'] = {
            x['schema_id']: [
                z['schema_field_id'] for z in x['schema_fields']
            ]
            for x in schema_struct.to_python(response.schema)
        }
    return result


def put_binary_type(
    connection: 'Connection', type_name: str, affinity_key_field: str=None,
    is_enum=False, schema: dict=None, query_id=None,
) -> APIResult:
    """
    Registers binary type information in cluster.

    :param connection: connection to Ignite server,
    :param type_name: name of the data type being registered,
    :param affinity_key_field: (optional) name of the affinity key field,
    :param is_enum: (optional) register enum if True, binary object otherwise.
     Defaults to False,
    :param schema: (optional) when register enum, pass a dict of enumerated
     parameter names as keys and an integers as values. When register binary
     type, pass a dict of field names: field types. Binary type with no fields
     is OK,
    :param query_id: (optional) a value generated by client and returned as-is
     in response.query_id. When the parameter is omitted, a random value
     is generated,
    :return: API result data object.
    """
    # prepare data
    if schema is None:
        schema = {}
    type_id = entity_id(type_name)
    data = {
        'type_name': type_name,
        'type_id': type_id,
        'affinity_key_field': affinity_key_field,
        'binary_fields': [],
        'is_enum': is_enum,
        'schema': [],
    }
    schema_id = None
    if is_enum:
        data['enums'] = []
        for literal, ordinal in schema.items():
            data['enums'].append({
                'literal': literal,
                'type_id': ordinal,
            })
    else:
        # assemble schema and calculate schema ID in one go
        schema_id = FNV1_OFFSET_BASIS if schema else 0
        for field_name, data_type in schema.items():
            # TODO: check for allowed data types
            field_id = entity_id(field_name)
            data['binary_fields'].append({
                'field_name': field_name,
                'type_id': int.from_bytes(
                    data_type.type_code,
                    byteorder=PROTOCOL_BYTE_ORDER
                ),
                'field_id': field_id,
            })
            schema_id ^= (field_id & 0xff)
            schema_id = int_overflow(schema_id * FNV1_PRIME)
            schema_id ^= ((field_id >> 8) & 0xff)
            schema_id = int_overflow(schema_id * FNV1_PRIME)
            schema_id ^= ((field_id >> 16) & 0xff)
            schema_id = int_overflow(schema_id * FNV1_PRIME)
            schema_id ^= ((field_id >> 24) & 0xff)
            schema_id = int_overflow(schema_id * FNV1_PRIME)

    data['schema'].append({
        'schema_id': schema_id,
        'schema_fields': [
            {'schema_field_id': entity_id(x)} for x in schema
        ],
    })

    # do query
    if is_enum:
        query_struct = Query(
            OP_PUT_BINARY_TYPE,
            [
                ('type_id', Int),
                ('type_name', String),
                ('affinity_key_field', String),
                ('binary_fields', binary_fields_struct),
                ('is_enum', Bool),
                ('enums', enum_struct),
                ('schema', schema_struct),
            ],
            query_id=query_id,
        )
    else:
        query_struct = Query(
            OP_PUT_BINARY_TYPE,
            [
                ('type_id', Int),
                ('type_name', String),
                ('affinity_key_field', String),
                ('binary_fields', binary_fields_struct),
                ('is_enum', Bool),
                ('schema', schema_struct),
            ],
            query_id=query_id,
        )
    result = query_struct.perform(connection, query_params=data)
    if result.status == 0:
        result.value = {
            'type_id': type_id,
            'schema_id': schema_id,
        }
    return result
