import pytest
import requests

import DMT.external.pypi as DMT_pypi


def test_get_pypi_url():
    with pytest.raises(IOError):
        DMT_pypi.get_pypi_url(package="foobarASCAUIPGFASO")

    assert (
        DMT_pypi.get_pypi_url(package="DMT-core", version="1.6.2")
        == "https://files.pythonhosted.org/packages/0b/06/d17b69543658705333c5752d516a9855e7efadf8c6de187c233e4a56b0fe/DMT_core-1.6.2-py3-none-any.whl"
    )

    assert (
        DMT_pypi.get_pypi_url(package="DMT-core", version="1.7.0")
        == "https://files.pythonhosted.org/packages/cb/1d/67ebecd8d14588b56675fb8d3f238059d69121eb36d3e250fd242d738d6d/DMT_core-1.7.0-py3-none-any.whl"
    )

    assert (
        DMT_pypi.get_pypi_url(package="DMT-core", version="1.7.0", pattern=".tar.gz")
        == "https://files.pythonhosted.org/packages/fd/f3/46ec1b19cdc5ef986f4f78e4273e1d22d649e1e692d6bd284d1d071a939d/DMT_core-1.7.0.tar.gz"
    )

    with pytest.raises(IOError):
        DMT_pypi.get_pypi_url(package="DMT-core", version="1.7.0", pattern=".foo") is None


def test_check_version():
    # valid versions
    assert DMT_pypi.check_version("900.9.9") == "900.9.9"
    assert DMT_pypi.check_version("900.9.9-rc.1") == "900.9.9-rc.1"

    # invalid versions
    with pytest.raises(IOError):
        DMT_pypi.check_version("0.1.0-pre.1")

    # not a release candidate version
    with pytest.raises(IOError):
        DMT_pypi.check_version("1.2.0-alpha.1")

    # equal or lower  as already released versions
    with pytest.raises(IOError):
        DMT_pypi.check_version("1.7.0")
    with pytest.raises(IOError):
        DMT_pypi.check_version("1.1.0")
    with pytest.raises(IOError):
        DMT_pypi.check_version("1.8.0-rc.1")


def test_extract_version():
    assert DMT_pypi.extract_version("Version_1.0.0") == "1.0.0"

    assert DMT_pypi.extract_version("Version_9.9.9") == "9.9.9"
    assert DMT_pypi.extract_version("Version_39.914.9123") == "39.914.9123"

    with pytest.raises(ValueError):
        DMT_pypi.extract_version("a.b.c")

    with pytest.raises(ValueError):
        DMT_pypi.extract_version("Version_1.0.0rc3")

    with pytest.raises(IOError):
        DMT_pypi.extract_version("Version_1.0.0-pre.1+build.2")

    with pytest.raises(IOError):
        DMT_pypi.extract_version("Version_1.0.0-alpha.1")


if __name__ == "__main__":
    test_get_pypi_url()
    test_extract_version()
    test_check_version()
