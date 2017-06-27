import pytest

from share.models.fields import EncryptedJSONField


class TestEncryptedJsonField:

    @pytest.fixture
    def field(self):
        return EncryptedJSONField(null=True, blank=True)

    def test_encrypt_and_decrypt_list(self, field):
        my_value = ['atom', {'elements': ['hydrogen', 'oxygen', 1.0, 2]}]
        assert isinstance(my_value, list)

        my_value_encrypted = field.get_db_prep_value(my_value)
        assert isinstance(my_value_encrypted, bytes)

        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert my_value_decrypted == my_value

    def test_encrypt_and_decrypt_dict_string_type(self, field):
        my_value = {'msg': u'hello'}
        assert isinstance(my_value, dict)

        my_value_encrypted = field.get_db_prep_value(my_value)
        assert isinstance(my_value_encrypted, bytes)

        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert isinstance(my_value_decrypted, dict)
        assert my_value_decrypted == my_value

    def test_encrypt_and_decrypt_unicode_in_string_type(self, field):
        my_value = {"model": u'찦차КЛМНО💁◕‿◕｡)╱i̲̬͇̪͙n̝̗͕v̟̜̘̦͟o̶̙̰̠kè͚̮̺̪̹̱̤  ǝɹol', "type": 'XE'}
        assert isinstance(my_value, dict)

        my_value_encrypted = field.get_db_prep_value(my_value)
        assert isinstance(my_value_encrypted, bytes)
        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert isinstance(my_value_decrypted, dict)
        assert my_value_decrypted == my_value
