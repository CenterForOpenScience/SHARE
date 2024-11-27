import abc
from unittest import TestCase
import typing


class BasicInputOutputTestCase(TestCase):
    '''base for tests that have a simple/repetitive input/output pattern
    '''
    maxDiff = None  # usually want the full diff for these tests, tho can override if you prefer

    # expected on subclasses:
    inputs: typing.ClassVar[
        dict[str, typing.Any]
    ]
    expected_outputs: typing.ClassVar[
        # keys should match `inputs` keys (enforce with types? maybe someday)
        dict[str, typing.Any]
    ]

    # required in subclasses
    @abc.abstractmethod
    def compute_output(self, given_input: typing.Any) -> typing.Any:
        raise NotImplementedError

    # (optional override, for when equality isn't so easy)
    def assert_outputs_equal(self, expected_output: typing.Any, actual_output: typing.Any) -> None:
        self.assertEqual(expected_output, actual_output)

    # (optional override, for when logic is more complicated)
    def run_input_output_test(self, given_input, expected_output):
        _actual_output = self.compute_output(given_input)
        self.assert_outputs_equal(expected_output, _actual_output)

    ###
    # private details

    def __init_subclass__(cls):
        # HACK: assign `test_*` method only on concrete subclasses,
        # so the test runner doesn't try instantiating a base class
        if getattr(cls, 'inputs', None) and getattr(cls, 'expected_outputs', None):
            cls.test_inputs_match_outputs = cls._test_inputs_match_outputs  # type: ignore[attr-defined]

    # the only actual test method -- assigned to concrete subclasses in __init_subclass__
    def _test_inputs_match_outputs(self):
        for _name, _input, _expected_output in self._iter_cases():
            with self.subTest(name=_name):
                self.run_input_output_test(_input, _expected_output)

    def _iter_cases(self) -> typing.Iterator[tuple[str, typing.Any, typing.Any]]:
        # yields (name, input, expected_output) tuples
        for _name, _input in self.inputs.items():
            try:
                _expected_output = self.expected_outputs[_name]
            except KeyError:
                raise NotImplementedError(f'{self.__class__.__qualname__}.expected_outputs["{_name}"]')
            yield (_name, _input, _expected_output)
