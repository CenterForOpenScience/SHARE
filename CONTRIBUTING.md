# CONTRIBUTING

## Style Guide

In the following templates, `TYPE` may be any of `Fix`, `Feature`, `Task`, or `Enhancement`.

### Commit Messages

Commit messages should be formatted as:

```
[SHARE-###][TYPE] Brief description

  * More details about the code changes.
  * Formatted as a bulleted list
  * If you have a really long line, wrap it
    at 80 characters and line up with the first
    letter, not the bullet point.
```

Here are some excellent commit messages, for reference.
* https://github.com/CenterForOpenScience/SHARE/commit/0fe503f0dc5f90da366246086ae76ee5281843cf
* https://github.com/CenterForOpenScience/SHARE/commit/226bac6a9010cde6aed7ac037c9186ac889b5132
* https://github.com/CenterForOpenScience/SHARE/commit/0e02dbb9d06920623e0dfb6a32fd1b38771de74b

### Pull Requests

Titles should be formatted as `[SHARE-###][TYPE] Brief description`

Here are some excellent pull requests, for reference.
* https://github.com/CenterForOpenScience/SHARE/pull/658
* https://github.com/CenterForOpenScience/SHARE/pull/642

### Code

#### Docstrings

Python docstrings should follow the [Google docstring style guide](http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).

To easily distinguish them, docstrings should use triple double-quotes, `"""`, and large strings should use triple single-quotes, `'''`

## Reporting Issues

If you find a bug in osf.io or would like to propose a new feature, please file an issue report in CenterForOpenScience/osf.io. Below we have some information on how to best report the issue, but if you’re short on time or new to this, don’t worry! We really want to know about the problem, so go ahead and report it. If you do this a lot, or you just want to know how to make it easier for us to find and fix the problem, keep reading.

If you would like to report a security issue, please email contact@cos.io for instructions on how to report the security issue. Do not include details of the issue in that email.

### Quick link
[Submit an issue](https://github.com/CenterForOpenScience/SHARE/issues/new?body=Steps%0A-------%0A1.%20%0A%0AExpected%0A------------%0A%0AActual%0A--------%0A)
using that link and you will have a handy template to save you a little time in your issue reporting.

### How to make the best issue
--------------------------

First, please make sure that the issue has not already been reported by searching through the issue archives.

When submitting an issue, be as descriptive as possible:
* What you did (step by step)
    * Where does this happen on SHARE?
* What you expected
* What actually happened
    * Check the JavaScript console in the browser (e.g. In Chrome go to View → Developer → JavaScript console) and report errors
    * If it's an issue with staging, report whether or not it also occurs on production
    * If an error was generated, report what time it occurred, and the specific URL.
* Potential causes
* Suggest a solution
    * What will it look like when this issue is resolved?

Include pictures (e.g., in OSX press Cmd+Shift+4 to draw a box to screenshot)


