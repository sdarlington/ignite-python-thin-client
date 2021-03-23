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

from pyignite.connection import AioConnection, Connection
from pyignite.datatypes import AnyDataArray, AnyDataObject, Bool, Byte, Int, Long, Map, Null, String, StructArray
from pyignite.datatypes.sql import StatementType
from pyignite.queries import Query, query_perform
from pyignite.queries.op_codes import (
    OP_QUERY_SCAN, OP_QUERY_SCAN_CURSOR_GET_PAGE, OP_QUERY_SQL, OP_QUERY_SQL_CURSOR_GET_PAGE, OP_QUERY_SQL_FIELDS,
    OP_QUERY_SQL_FIELDS_CURSOR_GET_PAGE, OP_RESOURCE_CLOSE
)
from pyignite.utils import cache_id, deprecated
from .result import APIResult
from ..queries.response import SQLResponse


def scan(conn: 'Connection', cache: Union[str, int], page_size: int, partitions: int = -1, local: bool = False,
         binary: bool = False, query_id: int = None) -> APIResult:
    """
    Performs scan query.

    :param conn: connection to Ignite server,
    :param cache: name or ID of the cache,
    :param page_size: cursor page size,
    :param partitions: (optional) number of partitions to query
     (negative to query entire cache),
    :param local: (optional) pass True if this query should be executed
     on local node only. Defaults to False,
    :param binary: (optional) pass True to keep the value in binary form.
     False by default,
    :param query_id: (optional) a value generated by client and returned as-is
     in response.query_id. When the parameter is omitted, a random value
     is generated,
    :return: API result data object. Contains zero status and a value
     of type dict with results on success, non-zero status and an error
     description otherwise.

     Value dict is of following format:

     * `cursor`: int, cursor ID,
     * `data`: dict, result rows as key-value pairs,
     * `more`: bool, True if more data is available for subsequent
       ‘scan_cursor_get_page’ calls.
    """
    return __scan(conn, cache, page_size, partitions, local, binary, query_id)


async def scan_async(conn: 'AioConnection', cache: Union[str, int], page_size: int, partitions: int = -1,
                     local: bool = False, binary: bool = False, query_id: int = None) -> APIResult:
    """
    Async version of scan.
    """
    return await __scan(conn, cache, page_size, partitions, local, binary, query_id)


def __query_result_post_process(result):
    if result.status == 0:
        result.value = dict(result.value)
    return result


def __scan(conn, cache, page_size, partitions, local, binary, query_id):
    query_struct = Query(
        OP_QUERY_SCAN,
        [
            ('hash_code', Int),
            ('flag', Byte),
            ('filter', Null),
            ('page_size', Int),
            ('partitions', Int),
            ('local', Bool),
        ],
        query_id=query_id,
    )
    return query_perform(
        query_struct, conn,
        query_params={
            'hash_code': cache_id(cache),
            'flag': 1 if binary else 0,
            'filter': None,
            'page_size': page_size,
            'partitions': partitions,
            'local': 1 if local else 0,
        },
        response_config=[
            ('cursor', Long),
            ('data', Map),
            ('more', Bool),
        ],
        post_process_fun=__query_result_post_process
    )


def scan_cursor_get_page(conn: 'Connection', cursor: int, query_id: int = None) -> APIResult:
    """
    Fetches the next scan query cursor page by cursor ID that is obtained
    from `scan` function.

    :param conn: connection to Ignite server,
    :param cursor: cursor ID,
    :param query_id: (optional) a value generated by client and returned as-is
     in response.query_id. When the parameter is omitted, a random value
     is generated,
    :return: API result data object. Contains zero status and a value
     of type dict with results on success, non-zero status and an error
     description otherwise.

     Value dict is of following format:

     * `data`: dict, result rows as key-value pairs,
     * `more`: bool, True if more data is available for subsequent
       ‘scan_cursor_get_page’ calls.
    """
    return __scan_cursor_get_page(conn, cursor, query_id)


async def scan_cursor_get_page_async(conn: 'AioConnection', cursor: int, query_id: int = None) -> APIResult:
    return await __scan_cursor_get_page(conn, cursor, query_id)


def __scan_cursor_get_page(conn, cursor, query_id):
    query_struct = Query(
        OP_QUERY_SCAN_CURSOR_GET_PAGE,
        [
            ('cursor', Long),
        ],
        query_id=query_id,
    )
    return query_perform(
        query_struct, conn,
        query_params={
            'cursor': cursor,
        },
        response_config=[
            ('data', Map),
            ('more', Bool),
        ],
        post_process_fun=__query_result_post_process
    )


@deprecated(version='1.2.0', reason="This API is deprecated and will be removed in the following major release. "
                                    "Use sql_fields instead")
def sql(
    conn: 'Connection', cache: Union[str, int],
    table_name: str, query_str: str, page_size: int, query_args=None,
    distributed_joins: bool = False, replicated_only: bool = False,
    local: bool = False, timeout: int = 0, binary: bool = False,
    query_id: int = None
) -> APIResult:
    """
    Executes an SQL query over data stored in the cluster. The query returns
    the whole record (key and value).

    :param conn: connection to Ignite server,
    :param cache: name or ID of the cache,
    :param table_name: name of a type or SQL table,
    :param query_str: SQL query string,
    :param page_size: cursor page size,
    :param query_args: (optional) query arguments,
    :param distributed_joins: (optional) distributed joins. Defaults to False,
    :param replicated_only: (optional) whether query contains only replicated
     tables or not. Defaults to False,
    :param local: (optional) pass True if this query should be executed
     on local node only. Defaults to False,
    :param timeout: (optional) non-negative timeout value in ms. Zero disables
     timeout (default),
    :param binary: (optional) pass True to keep the value in binary form.
     False by default,
    :param query_id: (optional) a value generated by client and returned as-is
     in response.query_id. When the parameter is omitted, a random value
     is generated,
    :return: API result data object. Contains zero status and a value
     of type dict with results on success, non-zero status and an error
     description otherwise.

     Value dict is of following format:

     * `cursor`: int, cursor ID,
     * `data`: dict, result rows as key-value pairs,
     * `more`: bool, True if more data is available for subsequent
       ‘sql_get_page’ calls.
    """

    if query_args is None:
        query_args = []

    query_struct = Query(
        OP_QUERY_SQL,
        [
            ('hash_code', Int),
            ('flag', Byte),
            ('table_name', String),
            ('query_str', String),
            ('query_args', AnyDataArray()),
            ('distributed_joins', Bool),
            ('local', Bool),
            ('replicated_only', Bool),
            ('page_size', Int),
            ('timeout', Long),
        ],
        query_id=query_id,
    )
    result = query_struct.perform(
        conn,
        query_params={
            'hash_code': cache_id(cache),
            'flag': 1 if binary else 0,
            'table_name': table_name,
            'query_str': query_str,
            'query_args': query_args,
            'distributed_joins': 1 if distributed_joins else 0,
            'local': 1 if local else 0,
            'replicated_only': 1 if replicated_only else 0,
            'page_size': page_size,
            'timeout': timeout,
        },
        response_config=[
            ('cursor', Long),
            ('data', Map),
            ('more', Bool),
        ],
    )
    if result.status == 0:
        result.value = dict(result.value)
    return result


@deprecated(version='1.2.0', reason="This API is deprecated and will be removed in the following major release. "
                                    "Use sql_fields instead")
def sql_cursor_get_page(
    conn: 'Connection', cursor: int, query_id: int = None,
) -> APIResult:
    """
    Retrieves the next SQL query cursor page by cursor ID from `sql`.

    :param conn: connection to Ignite server,
    :param cursor: cursor ID,
    :param query_id: (optional) a value generated by client and returned as-is
     in response.query_id. When the parameter is omitted, a random value
     is generated,
    :return: API result data object. Contains zero status and a value
     of type dict with results on success, non-zero status and an error
     description otherwise.

     Value dict is of following format:

     * `data`: dict, result rows as key-value pairs,
     * `more`: bool, True if more data is available for subsequent
       ‘sql_cursor_get_page’ calls.
    """

    query_struct = Query(
        OP_QUERY_SQL_CURSOR_GET_PAGE,
        [
            ('cursor', Long),
        ],
        query_id=query_id,
    )
    result = query_struct.perform(
        conn,
        query_params={
            'cursor': cursor,
        },
        response_config=[
            ('data', Map),
            ('more', Bool),
        ],
    )
    if result.status == 0:
        result.value = dict(result.value)
    return result


def sql_fields(
    conn: 'Connection', cache: Union[str, int],
    query_str: str, page_size: int, query_args=None, schema: str = None,
    statement_type: int = StatementType.ANY, distributed_joins: bool = False,
    local: bool = False, replicated_only: bool = False,
    enforce_join_order: bool = False, collocated: bool = False,
    lazy: bool = False, include_field_names: bool = False, max_rows: int = -1,
    timeout: int = 0, binary: bool = False, query_id: int = None
) -> APIResult:
    """
    Performs SQL fields query.

    :param conn: connection to Ignite server,
    :param cache: name or ID of the cache. If zero, then schema is used.
    :param query_str: SQL query string,
    :param page_size: cursor page size,
    :param query_args: (optional) query arguments. List of values or
     (value, type hint) tuples,
    :param schema: schema for the query.
    :param statement_type: (optional) statement type. Can be:

     * StatementType.ALL − any type (default),
     * StatementType.SELECT − select,
     * StatementType.UPDATE − update.

    :param distributed_joins: (optional) distributed joins.
    :param local: (optional) pass True if this query should be executed
     on local node only.
    :param replicated_only: (optional) whether query contains only
     replicated tables or not.
    :param enforce_join_order: (optional) enforce join order.
    :param collocated: (optional) whether your data is co-located or not.
    :param lazy: (optional) lazy query execution.
    :param include_field_names: (optional) include field names in result.
    :param max_rows: (optional) query-wide maximum of rows.
    :param timeout: (optional) non-negative timeout value in ms. Zero disables
     timeout.
    :param binary: (optional) pass True to keep the value in binary form.
    :param query_id: (optional) a value generated by client and returned as-is
     in response.query_id. When the parameter is omitted, a random value
     is generated,
    :return: API result data object. Contains zero status and a value
     of type dict with results on success, non-zero status and an error
     description otherwise.

     Value dict is of following format:

     * `cursor`: int, cursor ID,
     * `data`: list, result values,
     * `more`: bool, True if more data is available for subsequent
       ‘sql_fields_cursor_get_page’ calls.
    """
    return __sql_fields(conn, cache, query_str, page_size, query_args, schema, statement_type, distributed_joins,
                        local, replicated_only, enforce_join_order, collocated, lazy, include_field_names, max_rows,
                        timeout, binary, query_id)


async def sql_fields_async(
        conn: 'AioConnection', cache: Union[str, int],
        query_str: str, page_size: int, query_args=None, schema: str = None,
        statement_type: int = StatementType.ANY, distributed_joins: bool = False,
        local: bool = False, replicated_only: bool = False,
        enforce_join_order: bool = False, collocated: bool = False,
        lazy: bool = False, include_field_names: bool = False, max_rows: int = -1,
        timeout: int = 0, binary: bool = False, query_id: int = None
) -> APIResult:
    """
    Async version of sql_fields.
    """
    return await __sql_fields(conn, cache, query_str, page_size, query_args, schema, statement_type, distributed_joins,
                              local, replicated_only, enforce_join_order, collocated, lazy, include_field_names,
                              max_rows, timeout, binary, query_id)


def __sql_fields(conn, cache, query_str, page_size, query_args, schema, statement_type, distributed_joins, local,
                 replicated_only, enforce_join_order, collocated, lazy, include_field_names, max_rows, timeout,
                 binary, query_id):
    if query_args is None:
        query_args = []

    query_struct = Query(
        OP_QUERY_SQL_FIELDS,
        [
            ('hash_code', Int),
            ('flag', Byte),
            ('schema', String),
            ('page_size', Int),
            ('max_rows', Int),
            ('query_str', String),
            ('query_args', AnyDataArray()),
            ('statement_type', StatementType),
            ('distributed_joins', Bool),
            ('local', Bool),
            ('replicated_only', Bool),
            ('enforce_join_order', Bool),
            ('collocated', Bool),
            ('lazy', Bool),
            ('timeout', Long),
            ('include_field_names', Bool),
        ],
        query_id=query_id,
        response_type=SQLResponse
    )

    return query_perform(
        query_struct, conn,
        query_params={
            'hash_code': cache_id(cache),
            'flag': 1 if binary else 0,
            'schema': schema,
            'page_size': page_size,
            'max_rows': max_rows,
            'query_str': query_str,
            'query_args': query_args,
            'statement_type': statement_type,
            'distributed_joins': distributed_joins,
            'local': local,
            'replicated_only': replicated_only,
            'enforce_join_order': enforce_join_order,
            'collocated': collocated,
            'lazy': lazy,
            'timeout': timeout,
            'include_field_names': include_field_names,
        },
        include_field_names=include_field_names,
        has_cursor=True,
    )


def sql_fields_cursor_get_page(conn: 'Connection', cursor: int, field_count: int, query_id: int = None) -> APIResult:
    """
    Retrieves the next query result page by cursor ID from `sql_fields`.

    :param conn: connection to Ignite server,
    :param cursor: cursor ID,
    :param field_count: a number of fields in a row,
    :param query_id: (optional) a value generated by client and returned as-is
     in response.query_id. When the parameter is omitted, a random value
     is generated,
    :return: API result data object. Contains zero status and a value
     of type dict with results on success, non-zero status and an error
     description otherwise.

     Value dict is of following format:

     * `data`: list, result values,
     * `more`: bool, True if more data is available for subsequent
       ‘sql_fields_cursor_get_page’ calls.
    """
    return __sql_fields_cursor_get_page(conn, cursor, field_count, query_id)


async def sql_fields_cursor_get_page_async(conn: 'AioConnection', cursor: int, field_count: int,
                                           query_id: int = None) -> APIResult:
    """
    Async version sql_fields_cursor_get_page.
    """
    return await __sql_fields_cursor_get_page(conn, cursor, field_count, query_id)


def __sql_fields_cursor_get_page(conn, cursor, field_count, query_id):
    query_struct = Query(
        OP_QUERY_SQL_FIELDS_CURSOR_GET_PAGE,
        [
            ('cursor', Long),
        ],
        query_id=query_id,
    )
    return query_perform(
        query_struct, conn,
        query_params={
            'cursor': cursor,
        },
        response_config=[
            ('data', StructArray([(f'field_{i}', AnyDataObject) for i in range(field_count)])),
            ('more', Bool),
        ],
        post_process_fun=__post_process_sql_fields_cursor
    )


def __post_process_sql_fields_cursor(result):
    if result.status != 0:
        return result

    value = result.value
    result.value = {
        'data': [],
        'more': value['more']
    }
    for row_dict in value['data']:
        result.value['data'].append(list(row_dict.values()))
    return result


def resource_close(conn: 'Connection', cursor: int, query_id: int = None) -> APIResult:
    """
    Closes a resource, such as query cursor.

    :param conn: connection to Ignite server,
    :param cursor: cursor ID,
    :param query_id: (optional) a value generated by client and returned as-is
     in response.query_id. When the parameter is omitted, a random value
     is generated,
    :return: API result data object. Contains zero status on success,
     non-zero status and an error description otherwise.
    """
    return __resource_close(conn, cursor, query_id)


async def resource_close_async(conn: 'AioConnection', cursor: int, query_id: int = None) -> APIResult:
    return await __resource_close(conn, cursor, query_id)


def __resource_close(conn, cursor, query_id):
    query_struct = Query(
        OP_RESOURCE_CLOSE,
        [
            ('cursor', Long),
        ],
        query_id=query_id,
    )
    return query_perform(
        query_struct, conn,
        query_params={
            'cursor': cursor,
        }
    )
