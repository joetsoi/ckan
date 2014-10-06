'''Unit tests for ckan/logic/action/update.py.'''
import datetime

import nose.tools
import mock
import pylons.config as config

import ckan.logic as logic
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


assert_raises = nose.tools.assert_raises


def datetime_from_string(s):
    '''Return a standard datetime.datetime object initialised from a string in
    the same format used for timestamps in dictized activities (the format
    produced by datetime.datetime.isoformat())

    '''
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')


class TestUpdate(object):

    @classmethod
    def setup_class(cls):

        # Initialize the test db (if it isn't already) and clean out any data
        # left in it.
        # You should only do this in your setup_class() method if your test
        # class uses the db, most test classes shouldn't need to.
        helpers.reset_db()

    def setup(self):
        import ckan.model as model

        # Reset the db before each test method.
        # You should only do this in your setup() method if your test class
        # uses the db, most test classes shouldn't need to.
        model.repo.rebuild_db()

    def teardown(self):
        # Since some of the test methods below use the mock module to patch
        # things, we use this teardown() method to remove remove all patches.
        # (This makes sure the patches always get removed even if the test
        # method aborts with an exception or something.)
        mock.patch.stopall()

    ## START-AFTER

    def test_user_update_name(self):
        '''Test that updating a user's name works successfully.'''

        # The canonical form of a test has four steps:
        # 1. Setup any preconditions needed for the test.
        # 2. Call the function that's being tested, once only.
        # 3. Make assertions about the return value and/or side-effects of
        #    of the function that's being tested.
        # 4. Do nothing else!

        # 1. Setup.
        user = factories.User()

        # 2. Call the function that's being tested, once only.
        # FIXME we have to pass the email address and password to user_update
        # even though we're not updating those fields, otherwise validation
        # fails.
        helpers.call_action('user_update', id=user['name'],
                            email=user['email'],
                            password=factories.User.attributes()['password'],
                            name='updated',
                            )

        # 3. Make assertions about the return value and/or side-effects.
        updated_user = helpers.call_action('user_show', id=user['id'])
        # Note that we check just the field we were trying to update, not the
        # entire dict, only assert what we're actually testing.
        assert updated_user['name'] == 'updated'

        # 4. Do nothing else!

    ## END-BEFORE

    def test_user_generate_apikey(self):
        user = factories.User()
        context = {'user': user['name']}
        result = helpers.call_action('user_generate_apikey', context=context,
                                     id=user['id'])
        updated_user = helpers.call_action('user_show', context=context,
                                           id=user['id'])

        assert updated_user['apikey'] != user['apikey']
        assert result['apikey'] == updated_user['apikey']

    def test_user_generate_apikey_sysadmin_user(self):
        user = factories.User()
        sysadmin = factories.Sysadmin()
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        result = helpers.call_action('user_generate_apikey', context=context,
                                     id=user['id'])
        updated_user = helpers.call_action('user_show', context=context,
                                           id=user['id'])

        assert updated_user['apikey'] != user['apikey']
        assert result['apikey'] == updated_user['apikey']

    def test_user_generate_apikey_nonexistent_user(self):
        user = {'id': 'nonexistent', 'name': 'nonexistent', 'email':
                'does@notexist.com'}
        context = {'user': user['name']}
        nose.tools.assert_raises(logic.NotFound, helpers.call_action,
                                 'user_generate_apikey', context=context,
                                 id=user['id'])

    def test_user_update_with_id_that_does_not_exist(self):
        user_dict = factories.User.attributes()
        user_dict['id'] = "there's no user with this id"

        assert_raises(logic.NotFound, helpers.call_action,
                      'user_update', **user_dict)

    def test_user_update_with_no_id(self):
        user_dict = factories.User.attributes()
        assert 'id' not in user_dict
        assert_raises(logic.ValidationError, helpers.call_action,
                      'user_update', **user_dict)

    ## START-FOR-LOOP-EXAMPLE

    def test_user_update_with_invalid_name(self):
        user = factories.User()

        invalid_names = ('', 'a', False, 0, -1, 23, 'new', 'edit', 'search',
                         'a' * 200, 'Hi!', 'i++%')
        for name in invalid_names:
            user['name'] = name
            assert_raises(logic.ValidationError,
                          helpers.call_action, 'user_update',
                          **user)

    ## END-FOR-LOOP-EXAMPLE

    def test_user_update_to_name_that_already_exists(self):
        fred = factories.User(name='fred')
        bob = factories.User(name='bob')

        # Try to update fred and change his user name to bob, which is already
        # bob's user name
        fred['name'] = bob['name']
        assert_raises(logic.ValidationError, helpers.call_action,
                      'user_update', **fred)

    def test_user_update_password(self):
        '''Test that updating a user's password works successfully.'''

        user = factories.User()

        # FIXME we have to pass the email address to user_update even though
        # we're not updating it, otherwise validation fails.
        helpers.call_action('user_update', id=user['name'],
                            email=user['email'],
                            password='new password',
                            )

        # user_show() never returns the user's password, so we have to access
        # the model directly to test it.
        import ckan.model as model
        updated_user = model.User.get(user['id'])
        assert updated_user.validate_password('new password')

    def test_user_update_with_short_password(self):
        user = factories.User()

        user['password'] = 'xxx'  # This password is too short.
        assert_raises(logic.ValidationError, helpers.call_action,
                      'user_update', **user)

    def test_user_update_with_empty_password(self):
        '''If an empty password is passed to user_update, nothing should
        happen.

        No error (e.g. a validation error) is raised, but the password is not
        changed either.

        '''
        user_dict = factories.User.attributes()
        original_password = user_dict['password']
        user_dict = factories.User(**user_dict)

        user_dict['password'] = ''
        helpers.call_action('user_update', **user_dict)

        import ckan.model as model
        updated_user = model.User.get(user_dict['id'])
        assert updated_user.validate_password(original_password)

    def test_user_update_with_null_password(self):
        user = factories.User()

        user['password'] = None
        assert_raises(logic.ValidationError, helpers.call_action,
                      'user_update', **user)

    def test_user_update_with_invalid_password(self):
        user = factories.User()

        for password in (False, -1, 23, 30.7):
            user['password'] = password
            assert_raises(logic.ValidationError,
                          helpers.call_action, 'user_update',
                          **user)

    def test_user_update_without_email_address(self):
        '''You have to pass an email address when you call user_update.

        Even if you don't want to change the user's email address, you still
        have to pass their current email address to user_update.

        FIXME: The point of this feature seems to be to prevent people from
        removing email addresses from user accounts, but making them post the
        current email address every time they post to user update is just
        annoying, they should be able to post a dict with no 'email' key to
        user_update and it should simply not change the current email.

        '''
        user = factories.User()
        del user['email']

        assert_raises(logic.ValidationError,
                      helpers.call_action, 'user_update',
                      **user)

    # TODO: Valid and invalid values for the rest of the user model's fields.

    def test_user_update_activity_stream(self):
        '''Test that the right activity is emitted when updating a user.'''

        user = factories.User()
        before = datetime.datetime.now()

        # FIXME we have to pass the email address and password to user_update
        # even though we're not updating those fields, otherwise validation
        # fails.
        helpers.call_action('user_update', id=user['name'],
                            email=user['email'],
                            password=factories.User.attributes()['password'],
                            name='updated',
                            )

        activity_stream = helpers.call_action('user_activity_list',
                                              id=user['id'])
        latest_activity = activity_stream[0]
        assert latest_activity['activity_type'] == 'changed user'
        assert latest_activity['object_id'] == user['id']
        assert latest_activity['user_id'] == user['id']
        after = datetime.datetime.now()
        timestamp = datetime_from_string(latest_activity['timestamp'])
        assert timestamp >= before and timestamp <= after

    def test_user_update_with_custom_schema(self):
        '''Test that custom schemas passed to user_update do get used.

        user_update allows a custom validation schema to be passed to it in the
        context dict. This is just a simple test that if you pass a custom
        schema user_update does at least call a custom method that's given in
        the custom schema. We assume this means it did use the custom schema
        instead of the default one for validation, so user_update's custom
        schema feature does work.

        '''
        import ckan.logic.schema

        user = factories.User()

        # A mock validator method, it doesn't do anything but it records what
        # params it gets called with and how many times.
        mock_validator = mock.MagicMock()

        # Build a custom schema by taking the default schema and adding our
        # mock method to its 'id' field.
        schema = ckan.logic.schema.default_update_user_schema()
        schema['id'].append(mock_validator)

        # Call user_update and pass our custom schema in the context.
        # FIXME: We have to pass email and password even though we're not
        # trying to update them, or validation fails.
        helpers.call_action('user_update', context={'schema': schema},
                            id=user['name'], email=user['email'],
                            password=factories.User.attributes()['password'],
                            name='updated',
                            )

        # Since we passed user['name'] to user_update as the 'id' param,
        # our mock validator method should have been called once with
        # user['name'] as arg.
        mock_validator.assert_called_once_with(user['name'])

    def test_user_update_multiple(self):
        '''Test that updating multiple user attributes at once works.'''

        user = factories.User()

        params = {
            'id': user['id'],
            'name': 'updated_name',
            'fullname': 'updated full name',
            'about': 'updated about',
            # FIXME: We shouldn't have to put email here since we're not
            # updating it, but user_update sucks.
            'email': user['email'],
            # FIXME: We shouldn't have to put password here since we're not
            # updating it, but user_update sucks.
            'password': factories.User.attributes()['password'],
        }

        helpers.call_action('user_update', **params)

        updated_user = helpers.call_action('user_show', id=user['id'])
        assert updated_user['name'] == 'updated_name'
        assert updated_user['fullname'] == 'updated full name'
        assert updated_user['about'] == 'updated about'

    def test_user_update_does_not_return_password(self):
        '''The user dict that user_update returns should not include the user's
        password.'''

        user = factories.User()

        params = {
            'id': user['id'],
            'name': 'updated_name',
            'fullname': 'updated full name',
            'about': 'updated about',
            'email': user['email'],
            'password': factories.User.attributes()['password'],
        }

        updated_user = helpers.call_action('user_update', **params)
        assert 'password' not in updated_user

    def test_user_update_does_not_return_apikey(self):
        '''The user dict that user_update returns should not include the user's
        API key.'''

        user = factories.User()

        params = {
            'id': user['id'],
            'name': 'updated_name',
            'fullname': 'updated full name',
            'about': 'updated about',
            'email': user['email'],
            'password': factories.User.attributes()['password'],
        }

        updated_user = helpers.call_action('user_update', **params)
        assert 'apikey' not in updated_user

    def test_user_update_does_not_return_reset_key(self):
        '''The user dict that user_update returns should not include the user's
        reset key.'''

        import ckan.lib.mailer
        import ckan.model

        user = factories.User()
        ckan.lib.mailer.create_reset_key(ckan.model.User.get(user['id']))

        params = {
            'id': user['id'],
            'name': 'updated_name',
            'fullname': 'updated full name',
            'about': 'updated about',
            'email': user['email'],
            'password': factories.User.attributes()['password'],
        }

        updated_user = helpers.call_action('user_update', **params)
        assert 'reset_key' not in updated_user

    def test_resource_reorder(self):
        resource_urls = ["http://a.html", "http://b.html", "http://c.html"]
        dataset = {"name": "basic",
                   "resources": [{'url': url} for url in resource_urls]
                   }

        dataset = helpers.call_action('package_create', **dataset)
        created_resource_urls = [resource['url'] for resource
                                 in dataset['resources']]
        assert created_resource_urls == resource_urls
        mapping = dict((resource['url'], resource['id']) for resource
                       in dataset['resources'])

        ## This should put c.html at the front
        reorder = {'id': dataset['id'], 'order':
                   [mapping["http://c.html"]]}

        helpers.call_action('package_resource_reorder', **reorder)

        dataset = helpers.call_action('package_show', id=dataset['id'])
        reordered_resource_urls = [resource['url'] for resource
                                   in dataset['resources']]

        assert reordered_resource_urls == ["http://c.html",
                                           "http://a.html",
                                           "http://b.html"]

        reorder = {'id': dataset['id'], 'order': [mapping["http://b.html"],
                                                  mapping["http://c.html"],
                                                  mapping["http://a.html"]]}

        helpers.call_action('package_resource_reorder', **reorder)
        dataset = helpers.call_action('package_show', id=dataset['id'])

        reordered_resource_urls = [resource['url'] for resource
                                   in dataset['resources']]

        assert reordered_resource_urls == ["http://b.html",
                                           "http://c.html",
                                           "http://a.html"]


class TestGroupUpdateDatasetMembership(object):
    '''ckan#1907

    When calling group_update() for 'users', 'packages', 'groups', 'tags' and
    'extras':
      * providing a list will update the current membership of that key
      * the empty list [] will delete all membership of that key
      * when not specified, membership will remain the same
    '''
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        self.datasets = [factories.Dataset() for i in range(3)]
        self.group = factories.Group(packages=self.datasets)
        self.user = helpers.call_action('get_site_user')

    def teardown(self):
        helpers.reset_db()

    def test_providing_dataset_list_updates_dataset_membership(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.user['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
            packages=[
                {'name': self.datasets[0]['name']},
                {'name': self.datasets[1]['name']},
            ]
        )

        nose.tools.assert_equals(2, len(updated_group['packages']))

        names = set(i['name'] for i in updated_group['packages'])
        nose.tools.assert_equals(
            set(i['name'] for i in self.datasets[:2]),
            names
        )

    def test_empty_list_removes_all_dataset_members(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.user['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
            packages=[]
        )
        nose.tools.assert_equals([], updated_group['packages'])

    def test_that_no_dataset_key_in_data_dict_keeps_current_membership(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.user['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
        )
        nose.tools.assert_equals(3, len(updated_group['packages']))
        names = set(i['name'] for i in updated_group['packages'])
        nose.tools.assert_equals(set(i['name'] for i in self.datasets), names)


class TestGroupUpdateUserMembership(object):
    '''ckan#1907

    When calling group_update() for 'users', 'packages', 'groups', 'tags' and
    'extras':
      * providing a list will update the current membership of that key
      * the empty list [] will delete all membership of that key
      * when not specified, membership will remain the same
    '''
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        self.users = [factories.User() for i in range(3)]
        self.group = factories.Group(user=self.users[0],
                                     users=self.users)

    def teardown(self):
        helpers.reset_db()

    def test_providing_user_list_updates_user_membership(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.users[0]['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
            users=[
                {'name': self.users[0]['name']},
                {'name': self.users[1]['name']},
            ]
        )
        nose.tools.assert_equals(2, len(updated_group['users']))
        names = [i['name'] for i in updated_group['users']]
        nose.tools.assert_equals(
            [i['name'] for i in self.users[:2]],
            names
        )

    def test_empty_list_removes_all_user_members(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.users[0]['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
            users=[]
        )
        nose.tools.assert_equals([], updated_group['users'])

    def test_that_no_user_key_in_data_dict_keeps_current_user_membership(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.users[0]['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
        )
        nose.tools.assert_equals(3, len(updated_group['users']))
        names = [i['name'] for i in updated_group['users']]
        nose.tools.assert_equals([i['name'] for i in self.users], names)


class TestGroupUpdateSubGroups(object):
    '''ckan#1907

    When calling group_update() for 'users', 'packages', 'groups', 'tags' and
    'extras':
      * providing a list will update the current membership of that key
      * the empty list [] will delete all membership of that key
      * when not specified, membership will remain the same
    '''
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        self.subgroups = [factories.Group() for i in range(3)]
        self.group = factories.Group(groups=self.subgroups)
        self.user = helpers.call_action('get_site_user')

    def teardown(self):
        helpers.reset_db()

    def test_providing_list_of_groups_updates_subgroups(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.user['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
            groups=[
                {'name': self.subgroups[0]['name']},
                {'name': self.subgroups[1]['name']},
            ]
        )

        nose.tools.assert_equals(2, len(updated_group['groups']))

        names = set(i['name'] for i in updated_group['groups'])
        nose.tools.assert_equals(
            set(i['name'] for i in self.subgroups[:2]),
            names
        )

    def test_empty_list_removes_all_subgroups(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.user['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
            groups=[]
        )
        nose.tools.assert_equals([], updated_group['groups'])

    def test_that_no_groups_key_in_data_dict_keeps_current_groups(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.user['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
        )
        nose.tools.assert_equals(3, len(updated_group['groups']))
        names = set(i['name'] for i in updated_group['groups'])
        nose.tools.assert_equals(set(i['name'] for i in self.subgroups), names)


class TestGroupUpdateExtras(object):
    '''ckan#1907

    When calling group_update() for 'users', 'packages', 'groups', 'tags' and
    'extras':
      * providing a list will update the current membership of that key
      * the empty list [] will delete all membership of that key
      * when not specified, membership will remain the same
    '''
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        self.extras = [
            {'key': 'key_1', 'value': 'value'},
            {'key': 'key_2', 'value': 'value'},
            {'key': 'key_3', 'value': 'value'},
        ]
        self.group = factories.Group(extras=self.extras)
        self.user = helpers.call_action('get_site_user')

    def teardown(self):
        helpers.reset_db()

    def test_providing_list_of_extras_updates_group_extras(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.user['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
            extras=[
                {'key': 'key_1', 'value': 'value'},
                {'key': 'key_2', 'value': 'value'},
            ]
        )

        nose.tools.assert_equals(2, len(updated_group['extras']))

        names = set(i['key'] for i in updated_group['extras'])
        nose.tools.assert_equals(
            set(i['key'] for i in self.extras[:2]),
            names
        )

    def test_empty_list_removes_all_subgroups(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.user['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
            extras=[],
        )
        nose.tools.assert_equals([], updated_group['extras'])

    def test_that_no_groups_key_in_data_dict_keeps_current_groups(self):
        updated_group = helpers.call_action(
            'group_update',
            context={'user': self.user['name']},
            id=self.group['id'],
            # needs name as the call to form_to_db_schema is not passed as
            # 'api' in the context so the default_group_schema is used
            name=self.group['name'],
        )
        nose.tools.assert_equals(3, len(updated_group['extras']))
        names = set(i['key'] for i in updated_group['extras'])
        nose.tools.assert_equals(set(i['key'] for i in self.extras), names)


class TestUpdateSendEmailNotifications(object):
    @classmethod
    def setup_class(cls):
        cls._original_config = dict(config)
        config['ckan.activity_streams_email_notifications'] = True

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)

    @mock.patch('ckan.logic.action.update.request')
    def test_calling_through_paster_doesnt_validates_auth(self, mock_request):
        mock_request.environ.get.return_value = True
        helpers.call_action('send_email_notifications')

    @mock.patch('ckan.logic.action.update.request')
    def test_not_calling_through_paster_validates_auth(self, mock_request):
        mock_request.environ.get.return_value = False
        assert_raises(logic.NotAuthorized, helpers.call_action,
                      'send_email_notifications',
                      context={'ignore_auth': False})


class TestResourceViewUpdate(object):

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()

    def setup(cls):
        helpers.reset_db()

    def test_resource_view_update(self):
        resource_view = factories.ResourceView()
        params = {
            'id': resource_view['id'],
            'title': 'new title',
            'description': 'new description'
        }

        result = helpers.call_action('resource_view_update', **params)

        assert_equals(result['title'], params['title'])
        assert_equals(result['description'], params['description'])

    def test_resource_view_update_requires_id(self):
        params = {}

        nose.tools.assert_raises(logic.ValidationError,
                                 helpers.call_action,
                                 'resource_view_update', **params)

    def test_resource_view_update_requires_existing_id(self):
        params = {
            'id': 'inexistent_id'
        }

        nose.tools.assert_raises(logic.NotFound,
                                 helpers.call_action,
                                 'resource_view_update', **params)
