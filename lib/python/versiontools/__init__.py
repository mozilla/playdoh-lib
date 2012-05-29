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
versiontools
============

Define *single* and *useful* ``__version__`` of a project.

.. note: Since version 1.1 we should conform to PEP 386
"""

__version__ = (1, 9, 1, "final", 0)


import inspect
import operator
import os
import sys


class Version(tuple):
    """
    Smart version class.
    
    Version class is a tuple of five elements and has the same logical
    components as :data:`sys.version_info`.

    In addition to the tuple elements there is a special :attr:`vcs` attribute
    that has all of the data exported by the version control system.
    """

    _RELEASELEVEL_TO_TOKEN = {
        "alpha": "a",
        "beta": "b",
        "candidate": "c",
    }

    def __new__(cls, major, minor, micro=0, releaselevel="final", serial=0):
        """
        Construct a new version tuple.

        There is some extra logic when initializing tuple elements. All
        variables except for releaselevel are silently converted to integers
        That is::

            >>> Version("1.2.3.dev".split("."))
            (1, 2, 3, "dev", 0)

        :param major:
            Major version number

        :type major:
            :class:`int` or :class:`str`

        :param minor:
            Minor version number

        :type minor:
            :class:`int` or :class:`str`

        :param micro:
            Micro version number, defaults to ``0``.

        :type micro:
            :class:`int` or :class:`str`

        :param releaselevel:
            Release level name.

            There is a constraint on allowed values of releaselevel. Only the
            following values are permitted:

            * 'dev'
            * 'alpha'
            * 'beta'
            * 'candidate'
            * 'final'

        :type releaselevel:
            :class:`str`

        :param serial:
            Serial number, usually zero, only used for alpha, beta and
            candidate versions where it must be greater than zero.

        :type micro:
            :class:`int` or :class:`str`

        :raises ValueError:
            If releaselevel is incorrect, a version component is negative or
            serial is 0 and releaselevel is alpha, beta or candidate.
        """
        def to_int(v):
            v = int(v)
            if v < 0:
                raise ValueError("Version components cannot be negative")
            return v

        major = to_int(major)
        minor = to_int(minor)
        micro = to_int(micro)
        serial = to_int(serial)
        if releaselevel not in ('dev', 'alpha', 'beta', 'candidate', 'final'):
            raise ValueError(
                "releaselevel %r is not permitted" % (releaselevel,))
        if releaselevel in ('alpha', 'beta', 'candidate') and serial == 0:
            raise ValueError(
                ("serial must be greater than zero for"
                 " %s releases") % releaselevel)
        obj = tuple.__new__(cls, (major, minor, micro, releaselevel, serial))
        object.__setattr__(obj, '_source_tree', cls._find_source_tree())
        object.__setattr__(obj, '_vcs', None)
        return obj

    major = property(
        operator.itemgetter(0),
        doc="Major version number")

    minor = property(
        operator.itemgetter(1),
        doc="Minor version number")

    micro = property(
        operator.itemgetter(2),
        doc="Micro version number")

    releaselevel = property(
        operator.itemgetter(3),
        doc="Release level string")

    serial = property(
        operator.itemgetter(4),
        doc="Serial number")

    @property
    def vcs(self):
        """
        Return VCS integration object, if any.

        Accessing this attribute for the first time will query VCS lookup (may
        be slower, will trigger imports of various VCS plugins).

        The returned object, if not None, should have at least the `revno`
        property. For details see your particular version control integration
        plugin.

        .. note::
            This attribute is **not** an element of the version tuple
            and thus does not break sorting.

        .. versionadded:: 1.0.4
        """
        if self._vcs is None:
            self._vcs = self._query_vcs()
        return self._vcs

    @classmethod
    def from_tuple(cls, version_tuple):
        """
        Create version from 5-element tuple

        .. note::
            This method is identical to the constructor, just spelled in a way
            that is more obvious to use.

        .. versionadded:: 1.1
        """
        return cls(*version_tuple)

    @classmethod
    def from_tuple_and_hint(cls, version_tuple, hint):
        """
        Create version from a 5-element tuple and VCS location hint.

        Similar to :meth:`~versiontools.Version.from_tuple` but uses the hint
        object to locate the source tree if needed. A good candidate for hint
        object is the module that contains the version_tuple. In general
        anything that works with :meth:`inspect.getsourcefile()` is good.

        .. versionadded:: 1.4
        """
        self = cls.from_tuple(version_tuple)
        if self._source_tree is None:
            path = inspect.getsourcefile(hint)
            if path is not None:
                self._source_tree = os.path.dirname(os.path.abspath(path))
        return self

    @classmethod
    def from_expression(cls, pkg_expression):
        """
        Create a version from a python module name.

        The argument must describe a module to import. The module must declare
        a variable that holds the actual version. The version cannot be a plain
        string and instead must be a tuple of five elements as described by the
        :class:`~versiontools.Version` class.
        
        The variable that holds the version should be called ``__version__``.
        If it is called something else the actual name has to be specified
        explicitly in ``pkg_expression`` by appending a colon (``:``) and the
        name of the variable (for example ``package:version``).

        .. versionadded:: 1.9
        """
        # Parse the version string
        if ":" in pkg_expression:
            module_or_package, identifier = pkg_expression.split(":", 1)
        else:
            # Allow people not to include the identifier separator
            module_or_package = pkg_expression
            identifier = "" 
        # Use __version__ unless specified otherwise
        if identifier == "":
            identifier = "__version__"
        # Import module / package
        try:
            obj = __import__(module_or_package, globals(), locals(), [''])
        except ImportError:
            message = _get_exception_message(*sys.exc_info())
            raise ValueError(
                "Unable to import %r%s" % (module_or_package, message))
        # Look up the version identifier.
        try:
            version = getattr(obj, identifier)
        except AttributeError:
            message = _get_exception_message(*sys.exc_info())
            raise ValueError(
                "Unable to access %r in %r%s" % (
                    identifier, module_or_package, message))
        return cls.from_tuple_and_hint(version, hint=obj)

    def __str__(self):
        """
        Return a string representation of the version tuple.

        The string is not a direct concatenation of all version components.
        Instead it's a more natural 'human friendly' version where components
        with certain values are left out.

        The following table shows how a version tuple gets converted to a
        version string.

        +-------------------------------+-------------------+
        | __version__                   | Formatter version |
        +===============================+===================+
        | ``(1, 2, 0, "final", 0)``     | ``"1.2"``         |
        +-------------------------------+-------------------+
        | ``(1, 2, 3, "final", 0)``     | ``"1.2.3"``       |
        +-------------------------------+-------------------+
        | ``(1, 3, 0, "alpha", 1)``     | ``"1.3a1"``       |
        +-------------------------------+-------------------+
        | ``(1, 3, 0, "beta", 1)``      | ``"1.3b1"``       |
        +-------------------------------+-------------------+
        | ``(1, 3, 0, "candidate", 1)`` | ``"1.3c1"``       |
        +-------------------------------+-------------------+
        | ``(1, 3, 0, "dev", 0)``       | ``"1.3.dev"``     |
        +-------------------------------+-------------------+

        Now when release level is set to ``"dev"`` then interesting things
        start to happen.  When possible, version control system is queried for
        revision or changeset identifier. This information gets used to create
        a more useful version string. The suffix gets appended to the base
        version string. So for example a full version string, when using Bazaar
        might look like this: ``"1.3.dev54"`` which indicates that the tree was
        at revision 54 at that time.

        The following table describes what gets appended by each version
        control system.

        +-----------+------------------------------------------------+
        | VCS       | Formatted version suffix                       |
        +===========+================================================+
        | Bazaar    | Revision number (revno),  e.g. ``54``          |
        +-----------+------------------------------------------------+
        | Git       | Short commit ID of the current branch          |
        |           | e.g. ``"763fbe3"``                             |
        +-----------+------------------------------------------------+
        | Mercurial | Tip revision number, e.g. ``54``               |
        +-----------+------------------------------------------------+
        """
        version = "%s.%s" % (self.major, self.minor)
        if self.micro != 0:
            version += ".%s" % self.micro
        token = self._RELEASELEVEL_TO_TOKEN.get(self.releaselevel)
        if token:
            version += "%s%d" % (token, self.serial)
        if self.releaselevel == "dev":
            if self.vcs is not None:
                version += ".dev%s" % self.vcs.revno
            else:
                version += ".dev"
        return version

    @classmethod
    def _find_source_tree(cls):
        """
        Find the absolute pathname of the tree that contained the file that
        called our __init__()
        """
        frame = inspect.currentframe()
        outer_frames = inspect.getouterframes(frame)
        for index0, record in enumerate(outer_frames):
            frame, filename, lineno, func_name, context, context_index = record
            if context is None or context_index >= len(context):
                continue
            if (func_name == "<module>" and "__version__" in
                context[context_index]):
                caller = frame
                break
        else:
            caller = None
        if caller:
            return os.path.dirname(
                os.path.abspath(
                    inspect.getsourcefile(caller)))

    def _query_vcs(self):
        """
        Attempt to build a VCS object for the directory refrenced in
        self._source_tree.

        The actual version control integration is pluggable, anything that
        provides an entrypoint for ``versintools.vcs_integration`` is
        considered. The first version control system that indicates support for
        the directory wins.

        In practice you'd want to use the vcs property.
        """
        import pkg_resources
        if self._source_tree is None:
            return
        for entrypoint in pkg_resources.iter_entry_points(
            "versiontools.vcs_integration"):
            try:
                integration_cls = entrypoint.load()
                integration = integration_cls.from_source_tree(
                    self._source_tree)
                if integration:
                    return integration
            except ImportError:
                pass


def format_version(version, hint=None):
    """
    Pretty formatting for 5-element version tuple.

    Instead of using :class:`~versiontools.Version` class directly you may want
    to use this simplified interface where you simply interpret an arbitrary
    five-element version tuple as a version to get the pretty and
    :pep:`386`-compliant version string.

    :param version:
        The version to format

    :type version:
        A :class:`tuple` with five elements, as the one provided to
        :meth:`versiontools.Version.from_tuple`, or an existing instance of
        :class:`versiontools.Version`.

    :param hint:
        The hint object, if provided, helps versiontools to locate the
        directory which might host the project's source code. The idea is to
        pass `module.__version__` as the first argument and `module` as the
        hint. This way we can lookup where module came from, and look for
        version control system data in that directory. Technically passing hint
        will make us call :meth:`~versiontools.Version.from_tuple_and_hint()`
        instead of :meth:`~versiontools.Version.from_tuple()`.

    :type hint:
        either :obj:`None`, or a module.

    .. versionadded:: 1.1
    """
    if isinstance(version, Version):
        return str(version)
    elif isinstance(version, tuple) and len(version) == 5 and hint is not None:
        return str(Version.from_tuple_and_hint(version, hint))
    elif isinstance(version, tuple) and len(version) == 5:
        return str(Version.from_tuple(version))
    else:
        raise ValueError("version must be a tuple of five items")


def _get_exception_message(exception, value, traceback):
    """
    Helper for compatibility with older python versions
    """
    if value is not None:  # the exception value
        return ": %s" % value
    return ""


from versiontools.setuptools_hooks import version as handle_version
