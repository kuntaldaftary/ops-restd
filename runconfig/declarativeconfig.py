from opsrest.constants import *
from opsrest.utils import utils
import urllib
import types


def _get_row_data(row, table_name, schema, idl, index=None):

    if index is None:
        index = utils.row_to_index(row, table_name, schema, idl)

    row_data = {}

    # Routes are special case - only static routes are returned
    if table_name == 'Route' and row.__getattr__('from') != 'static':
        return

    # Iterate over all columns in the row
    table_schema = schema.ovs_tables[table_name]
    for column_name in table_schema.config.keys():
        column_data = row.__getattr__(column_name)

        # Do not include empty columns
        if column_data is None or column_data == {} or column_data == []:
            continue

        row_data[column_name] = column_data

    # Iterate over all children (forward and backward references) in the row
    for child_name in table_schema.children:

        # Forward reference
        # Two types of forward references exist
        # - regular (List of uuid)
        # - key/value type (Dict type)

        children_data = {}
        if child_name in table_schema.references:

            # Only include configurable children
            if (
                table_schema.references[child_name].category
                != OVSDB_SCHEMA_CONFIG
            ):
                continue

            column_data = row.__getattr__(child_name)
            child_table_name = table_schema.references[child_name].ref_table

            # Check kv_type references
            keys = None
            kv_type = table_schema.references[child_name].kv_type
            if kv_type and isinstance(column_data, dict):
                keys = column_data.keys()
                column_data = column_data.values()

            # Iterate through all items in column_data
            count = 0
            for item in column_data:
                if kv_type:
                    kv_index = keys[count]
                    data = _get_row_data(
                        item, child_table_name, schema,
                        idl, kv_index)
                    children_data.update({keys[count]: data.values()[0]})
                    count = count + 1
                else:
                    data = _get_row_data(item, child_table_name, schema, idl)
                    children_data.update(data)

        # Backward reference
        else:
            column_name = None
            # Find the 'parent' name from child table (back referenced child)
            # e.g. in Route table 'vrf' column is the 'parent' column
            for (name,
                    column) in (schema.ovs_tables[child_name].
                                references.iteritems()):
                if column.relation == OVSDB_SCHEMA_PARENT:
                    # Found the parent column
                    column_name = name
                    break

            # Iterate through entire child table to find those rows belonging
            # to the same parent
            for item in idl.tables[child_name].rows.itervalues():
                # Get the parent row reference
                ref = item.__getattr__(column_name)
                # Parent reference is same as 'row' (row was passed to
                #this function) this is now the child of 'row'
                if ref.uuid == row.uuid:
                    data = _get_row_data(item, child_name, schema, idl)
                    if data is not None:
                        children_data.update(data)

        if children_data:
            row_data[child_name] = children_data

    # Iterate through 'references' from table
    for refname, refobj in table_schema.references.iteritems():

        refdata = []
        if (
            refobj.relation == OVSDB_SCHEMA_REFERENCE
            and refobj.category == OVSDB_SCHEMA_CONFIG
        ):
            reflist = row.__getattr__(refname)

            if len(reflist) == 0:
                continue

            ref_table_name = table_schema.references[refname].ref_table
            for item in reflist:
                key_index = utils.row_to_index(
                    item, ref_table_name, schema, idl)
                refdata.append(key_index)

            row_data[refname] = refdata

    return {index: row_data}


def _get_table_data(table_name, schema, idl):

    # get the table from the DB
    table = idl.tables[table_name]

    # Iterate over all rows
    table_data = {table_name: {}}

    # If table is empty return None
    if len(table.rows) == 0:
        return None

    for row in table.rows.itervalues():
        row_data = _get_row_data(row, table_name, schema, idl)
        if row_data is None or row_data == [] or row_data == {}:
            continue
        table_data[table_name].update(row_data)

    return table_data


def read(schema, idl):
    '''
    Return running configuration
    '''

    config = {}
    for table_name in schema.ovs_tables.keys():

    # Check only root table or top level table
        if schema.ovs_tables[table_name].parent is not None:
            continue

    # Get table data for root or top level table
        table_data = _get_table_data(table_name, schema, idl)

        if table_data is not None:
            config.update(table_data)

    # remove system uuid
    config['System'] = config['System'].values()[0]
    return config
