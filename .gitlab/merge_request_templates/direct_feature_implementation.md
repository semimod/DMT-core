## Summary

(Summarize the feature you implemented)

## Application

(Name example application(s) for the feature)

## Implemented API

(Write an example Python code which uses the feature )

```python
from DMT import XXXX

....
```

## Implementation details

(If possible, link to your fork of DMT where you implement the wanted feature. Please list the changes you made.)

### Test case

(Create an test case for the new feature and link or paste it here.)

## Optimal items to check (for large new feature)

* [ ] All new dependencies are added to `setup.py`
* [ ] The new code is formatted using `black .`
* [ ] The new code is documented in the functions (and for large changes also in the documentation) (`cd doc && make html`)
* [ ] The current CI from the main branch can be run on my machine (`pytest test/test_core_no_interfaces/*.py` and if possible the interfaces).
* [ ] The new test case passes the new feature with a coverage of > 90% (`pytest --cov=DMT/path_to_new_feature test/path_to_new_test`).
* [ ] I increased the version of `DMT` according to [SemVer](http://semver.org/) (bug fixes / release candidate).
* [ ] I added the change to the `CHANGELOG`


/label ~feature_request
/assign @mario.k