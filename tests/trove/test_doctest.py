import doctest

import trove.util.chainmap
import trove.util.frozen
import trove.util.iris
import trove.util.propertypath

_DOCTEST_OPTIONFLAGS = (
    doctest.ELLIPSIS
    | doctest.NORMALIZE_WHITESPACE
)

_MODULES_WITH_DOCTESTS = (
    trove.util.chainmap,
    trove.util.frozen,
    trove.util.iris,
    trove.util.propertypath,
)


def _make_test_fn(testcase):
    def _test():
        _result = testcase.run()
        for _error_testcase, _traceback in _result.errors:
            print(f'ERROR({_error_testcase}):\n{_traceback}')
        for _error_testcase, _traceback in _result.failures:
            print(f'FAILURE({_error_testcase}):\n{_traceback}')
        assert not _result.failures and not _result.errors
    return _test


for _module in _MODULES_WITH_DOCTESTS:
    # HACK: allow running with pytest
    globals().update({
        f'test_doctest_{_module.__name__}_{_i}': _make_test_fn(_test_case)
        for _i, _test_case in enumerate(doctest.DocTestSuite(_module, optionflags=_DOCTEST_OPTIONFLAGS))
    })
