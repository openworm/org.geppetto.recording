"""Utility functions for org.geppetto.recording."""

import os
import runpy
import string
import sys
import math


def is_text_file(filename):
    """Return `True` if the file is text, `False` if it is binary."""
    with open(filename, 'r') as f:
        test_string = f.read(512)
        text_characters = ''.join(map(chr, range(32, 127)) + ['\n', '\r', '\t', '\b'])
        null_translation = string.maketrans('', '')
        if not test_string:  # empty file -> text
            return True
        if '\0' in test_string:  # file with null byte -> binary
            return False
        non_text_characters = test_string.translate(null_translation, text_characters)
        if float(len(non_text_characters)) / float(len(test_string)) > 0.30:  # more than 30% non-text characters -> binary
            return False
        else:
            return True


def make_iterable(object):
    """Return a list that holds the object, or the object itself if it is already iterable."""
    if hasattr(object, '__iter__'):
        return object
    else:
        return [object]


def run_as_script(filename):
    """Run a Python file as if it would be run from the command line (with name __main__ and its working directory)."""
    abspath = os.path.abspath(filename)
    dirname = os.path.dirname(abspath)
    sys.path.append(dirname)
    old_cwd = os.getcwd()
    os.chdir(dirname)
    vars_dict = runpy.run_path(abspath, run_name='__main__')
    os.chdir(old_cwd)
    sys.path.remove(dirname)
    return vars_dict


def split_by_separators(s, separators=(' ', ',', ';', '\t')):
    """Split a string by all elements in `separators` (or any combination) and return a list of the substrings."""
    if not hasattr(separators, '__iter__'):
        separators = make_iterable(separators)

    substrings = []

    while s:
        next_separator_start = -1
        next_separator_end = -1

        for separator in separators:
            separator_start = s.find(separator)
            if separator_start != -1 and (next_separator_start == -1 or separator_start < next_separator_start):
                next_separator_start = separator_start
                next_separator_end = separator_start + len(separator)

        if next_separator_start == -1:
            substrings.append(s)
            return substrings
        elif next_separator_start:
            substrings.append(s[:next_separator_start])
        s = s[next_separator_end:]

    return substrings


def pad_number(number, padding):
    """

    Parameters
    ----------
    number : integer
        Number to pad.
    padding : integer
        Padding dimension.

    Returns
    -------
    String
        The padded string

    """

    result = "0"

    if number != 0:
        while math.pow(10, padding) > number:
            result += "0"
            padding -= 1
    else:
        for i in range(0, padding):
            result += "0"

    result += str(number)

    return result