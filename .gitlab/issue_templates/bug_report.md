## Summary

(Summarize the bug encountered concisely)

## Steps to reproduce

(How one can reproduce the issue - this is very important)

## Environment (please complete the following information):
 - OS: [e.g. macOS, Linux, Windows]
 - Python Version: [3.8, 3.9, 3.10]
 - DMT version [e.g. 1.5.0]
 - (pip freeze)
 - Used interface versions: [eg. ngspice-36, ...]

## Example Project

(If possible, please create an example project/file that exhibits the problematic
behavior, and link to it here in the bug report.)

## What is the current bug behavior?

(What actually happens)

## What is the expected correct behavior?

(What you should see instead)

## Relevant logs and/or screenshots

(Paste any relevant logs - please use code blocks (```) to format console output, logs, and code, as
it's very hard to read otherwise.

You can activate the logging package using:

```python
import logging
# --->Setup for log
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=PATH_TO_LOG_FILE,
    filemode="w",
)
```
Paste this together with other relevant stuff.
)

## Possible fixes

(If you can, link to the line of code that might be responsible for the problem)

/label ~bug ~reproduced ~needs-investigation
/assign @mario.k