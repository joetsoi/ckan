import mock
import nose
from sqlalchemy.sql.elements import TextClause

import ckan.new_tests.helpers as helpers

import ckanext.datastore.db as db

assert_equal = nose.tools.assert_equal


class TestCreateIndexes(object):
    def test_creates_fts_index_by_default(self):
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('_full_text', connection, resource_id)

    @helpers.change_config('ckan.datastore.default_fts_lang', None)
    @mock.patch('ckanext.datastore.db._get_fields')
    def test_creates_fts_index_on_textual_fields_with_english_as_default(self, _get_fields):
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
            {'id': 'bar', 'type': 'number'}
        ]
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('foo', connection, resource_id, 'english')

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    @mock.patch('ckanext.datastore.db._get_fields')
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_with_config_var(self, _get_fields):
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
            {'id': 'bar', 'type': 'number'}
        ]
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('foo', connection, resource_id, 'simple')

    @helpers.change_config('ckan.datastore.default_fts_lang', 'simple')
    @mock.patch('ckanext.datastore.db._get_fields')
    def test_creates_fts_index_on_textual_fields_can_overwrite_lang_using_lang_param(self, _get_fields):
        _get_fields.return_value = [
            {'id': 'foo', 'type': 'text'},
            {'id': 'bar', 'type': 'number'}
        ]
        connection = mock.MagicMock()
        context = {
            'connection': connection
        }
        resource_id = 'resource_id'
        data_dict = {
            'resource_id': resource_id,
            'lang': 'french',
        }

        db.create_indexes(context, data_dict)

        self._assert_created_index_on('foo', connection, resource_id, 'french')

    def _assert_created_index_on(self, field, connection, resource_id, lang=None):
        if lang is not None:
            sql_str = u'ON "resource_id" USING gist(to_tsvector(:lang, :field))'
        else:
            sql_str = u'USING gist({field})'.format(field=field)

        calls = connection.execute.call_args_list
        fts_calls = [call for call in calls if isinstance(call[0][0], TextClause)]

        was_called = False
        for call in fts_calls:
            if call[0][0].text.find(sql_str) != -1:
                if lang is not None:
                    assert lang == call[1]['lang']
                    assert field == call[1]['field']
                was_called = True

        assert was_called, ("Expected 'connection.execute' to have been ",
                            "called with a string containing '%s'" % sql_str)
