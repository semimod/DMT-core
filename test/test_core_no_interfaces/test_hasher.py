""" Testing the hashing class
"""
import os
from DMT.core import create_md5_hash


def test_base():
    file_name = "test.txt"
    with open(file_name, "w") as my_test_file:
        my_test_file.write("test input")

    test_hash = create_md5_hash(file_name, b"example further info")
    assert test_hash == "fd862d8ec7e0ee8cf80aee9408908080"

    test_hash = create_md5_hash(file_name, "example further info")
    assert test_hash == "8242dfc8844947a6aaa3b053e987cf81"

    test_hash = create_md5_hash(file_name, "example further info", 465443)
    assert test_hash == "d3c6394dca24b36e155fc529f187fd17"

    os.remove(file_name)


def test_va_file():
    file_name = "test.txt"
    with open(file_name, "w") as my_test_file:
        my_test_file.write("test input")
    file_name2 = "va_file1.va"
    with open(file_name2, "w") as my_test_file:
        my_test_file.write("test va input 1")
    file_name3 = "va_file2.va"
    with open(file_name3, "w") as my_test_file:
        my_test_file.write("test va input 1")

    test_hash = create_md5_hash(file_name, file_name2)
    assert test_hash == "57649e3096bfd7fd4a17731936e709f7"

    test_hash = create_md5_hash(file_name, file_name2, file_name3)
    assert test_hash == "026beecca8a7ced367e855a484180206"

    os.remove(file_name)
    os.remove(file_name2)
    os.remove(file_name3)


def test_va_content():
    file_name = "test.txt"
    with open(file_name, "w") as my_test_file:
        my_test_file.write("test input")
    file_content1 = "test va input 1"
    file_content2 = "test va input 2"

    test_hash = create_md5_hash(file_name, file_content1)
    assert test_hash == "57649e3096bfd7fd4a17731936e709f7"

    test_hash = create_md5_hash(file_name, file_content1, file_content2)
    assert test_hash == "694a49fc36908036a9aa39b5584e1018"

    os.remove(file_name)


# test case
if __name__ == "__main__":
    test_base()
    test_va_file()
    test_va_content()
