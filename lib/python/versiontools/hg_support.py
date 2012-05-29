# -*- coding: utf-8 -*-"
# Copyright (C) 2011 enn.io UG (haftungsbeschränkt)
# Copyright (C) 2011-2012 Linaro Limited
#
# Author: Jannis Leidel <jannis@leidel.info>
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
.. _hg:

versiontools.hg_support
=======================

Mercurial (Hg) support for versiontools.

.. note::

    To work with Mercurial repositories you will need `Mercurial
    <http://mercurial.selenic.com/>`_. You can install it with pip or from the
    `mercurial` package on Ubuntu. 
"""
import logging
import sys


class HgIntegration(object):
    """
    Hg integration for versiontools
    """
    def __init__(self, repo):
        tip = repo.changectx('tip')
        self._revno = tip.rev()
        try:
            self._branch_nick = tip.branch()
        except Exception:
            self._branch_nick = None

    @property
    def revno(self):
        """
        Revision number of the branch
        """
        return self._revno

    @property
    def branch_nick(self):
        """
        Nickname of the branch

        .. versionadded:: 1.0.4
        """
        return self._branch_nick

    @classmethod
    def from_source_tree(cls, source_tree):
        """
        Initialize :class:`~versiontools.hg_support.HgIntegration` by
        pointing at the source tree.  Any file or directory inside the
        source tree may be used.
        """
        repo = None
        try:
            from mercurial.hg import repository
            from mercurial.ui import ui
            repo = repository(ui(), source_tree)
        except Exception:
            from versiontools import _get_exception_message
            message = _get_exception_message(*sys.exc_info())
            logging.debug("Unable to get branch revision because "
                          "directory %r is not a hg repo. Error: %s",
                          (source_tree, message))
        if repo:
            return cls(repo)
