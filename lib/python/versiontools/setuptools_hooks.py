# Copyright (C) 2010-2012 Linaro Limited
#
# Author: Zygmunt Krynicki <zygmunt.krynicki@linaro.org>
#
# This file is part of versiontools.
#
# versiontools is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation
#
# versiontools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with versiontools.  If not, see <http://www.gnu.org/licenses/>.

"""
versiontools.setuptools_hooks
=============================

Plugins for setuptools that add versintools features.

Setuptools has a framework where external packages, such as versiontools, can
hook into setup.py metadata and commands. We use this feature to intercept
special values of the ``version`` keyword argument to ``setup()``. This
argument handled by the following method:
"""

import sys

from distutils.errors import DistutilsSetupError
from versiontools import Version, _get_exception_message


def version(dist, attr, value):
    """
    Handle the ``version`` keyword to setuptools.setup()

    .. note::
        This function is normally called by setuptools, it is advertised in the
        entry points of versiontools as setuptools extension. There is no need
        to call in manually.

    .. versionadded:: 1.3
    """
    # We need to look at dist.metadata.version to actually see the version
    # that was passed to setup. Something in between does not seem to like our
    # version string and we get 0 here, odd.
    if value == 0:
        value = dist.metadata.version
    if sys.version_info[:1] < (3,):
        isstring = lambda string: isinstance(string, basestring)
    else:
        isstring = lambda string: isinstance(string, str)
    if not (isstring(value)
            and value.startswith(":versiontools:")):
        return
    # Peel away the magic tag
    value = value[len(":versiontools:"):]
    try:
        # Lookup the version object
        version = Version.from_expression(value)
        # Update distribution metadata
        dist.metadata.version = str(version) 
    except ValueError:
        message = _get_exception_message(*sys.exc_info())
        if message.startswith(": "):
            message = message[2:]
        raise DistutilsSetupError(message)
