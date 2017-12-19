import pytest

from share.models.fields import EncryptedJSONField


class TestEncryptedJsonField:

    @pytest.fixture
    def field(self):
        return EncryptedJSONField(null=True, blank=True)

    @pytest.mark.parametrize('input_text, output_text, isempty', [
        (['atom', {'elements': ['hydrogen', 'oxygen', 1.0, 2]}], ['atom', {'elements': ['hydrogen', 'oxygen', 1.0, 2]}], False),
        ({'msg': u'hello'}, {'msg': u'hello'}, False),
        ({"model": u'찦차КЛМНО💁◕‿◕｡)╱i̲̬͇̪͙n̝̗͕v̟̜̘̦͟o̶̙̰̠kè͚̮̺̪̹̱̤  ǝɹol', "type": 'XE'}, {"model": u'찦차КЛМНО💁◕‿◕｡)╱i̲̬͇̪͙n̝̗͕v̟̜̘̦͟o̶̙̰̠kè͚̮̺̪̹̱̤  ǝɹol', "type": 'XE'}, False),
        ({}, None, True),
        ('', None, True),
        ([], None, True),
        (set(), None, True)
    ])
    def test_encrypt_and_decrypt(self, field, input_text, output_text, isempty):
        my_value_encrypted = field.get_db_prep_value(input_text)

        if isempty:
            assert my_value_encrypted is None
        else:
            assert isinstance(my_value_encrypted, bytes)

        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert my_value_decrypted == output_text
