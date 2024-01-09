# Copyright (c) 2024 ANSYS, Inc. All rights reserved
"""This module defines project-level ccl constants."""

import re

ALLOWED_OPTION_LIST = "Allowed Option List"
ALLOWED_PARENT_LIST = "Allowed Parent List"
CATEGORY = "Category"
CCL_FALSE_VALUE_LIST = ("no", "false", "n", "f", "off", "0")
CCL_INDENT = "  "
CCL_TRUE_VALUE_LIST = ("yes", "true", "y", "t", "on", "1")
CONTEXT_RULE = "Context Rule"
DEFAULT = "Default"
DESCRIPTION = "Description"
ESSENTIAL_PARAMETER_LIST = "Essential Parameter List"
INTERNAL_PARAMETER_LIST = "Internal Parameter List"
OPTION = "Option"
OPTIONAL_PARAMETER_LIST = "Optional Parameter List"
PARAMETER_TYPE = "Parameter Type"
PARAMETER_TYPE_INTEGER = "Integer"
PARAMETER_TYPE_LOGICAL = "Logical"
PARAMETER_TYPE_REAL = "Real"
PARAMETER_TYPE_STRING = "String"
REMOTE_TYPE = "Remote Type"
REMOTE_TYPE_EXPRESSION = "expression"
# Regular expressions used in parsing ccl state
# TODO: Need to deal with more complex object definitions such as the following
"""
  FLUID PAIR: Water Steam 1 | Water at RTP
    My Parameter = 3 # catch the comment
    MyA.B = asdf  # This is allowed in Pre's USER object
    THIS IS A VERY LONG OBJECT TYPE: \
      Followed by a very long object name
      My Parameter Name = \
      asdf # not sure about this one
      My Other Parameter = asdf\
      asdf # be careful that the resulting value is asdfasdf with no space
    END
  END # fluid pair obj
"""
RE_OBJECT_START_STATE = re.compile(r"^\s*([A-Z]+[A-Z\s0-9]*?)\s*:\s*([A-Za-z][\w .]*)?\s*$")
RE_OBJECT_START_RULES = re.compile(r"^\s*([A-Z]+[A-Z ]*?)\s*:\s*([A-Za-z][A-Za-z0-9 ]*)?\s*$")
RE_OBJECT_END = re.compile(r"^\s*(?:END)\s*$")
RE_OBJECT_PARAM_DEF = re.compile(r"^\s*([A-Z][A-Za-z0-9 ]*?)\s*=\s*(.*?)\s*$")
RE_OBJECT_DEF_LINE_CONT = re.compile(r"(.*)\\\s*$")
RE_LINE_WITH_TRAILING_COMMENT = re.compile(r"(^\s*[^\s#].*?)\s*#.*$")
