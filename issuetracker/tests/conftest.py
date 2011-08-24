# -*- coding: utf-8 -*-
# Copyright (c) 2011, Sebastian Wiesner <lunaryorn@googlemail.com>
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (print_function, division, unicode_literals,
                        absolute_import)

import os

import pytest
import py.path
from mock import Mock
from lxml import etree
from pyquery import PyQuery
from sphinx.application import Sphinx
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment import SphinxStandaloneReader

from sphinxcontrib.issuetracker import Issue, IssuesReferences


TEST_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


def assert_issue_reference(doctree, issue, title=False):
    __tracebackhide__ = True
    reference = doctree.find('reference')
    assert len(reference) == 1
    assert reference.attr.refuri == issue.url
    classes = reference.attr.classes.split(' ')
    is_closed = 'issue-closed' in classes
    assert 'reference-issue' in classes
    assert issue.closed == is_closed
    if title:
        assert reference.text() == issue.title
    else:
        assert reference.text() == '#{0}'.format(issue.id)
    return reference


def get_doctree_as_xml(app, docname):
    return etree.fromstring(str(app.env.get_doctree(docname)))


def get_doctree_as_pyquery(app, docname):
    tree = get_doctree_as_xml(app, docname)
    return PyQuery(tree)


def pytest_namespace():
    return dict((f.__name__, f) for f in
                (get_doctree_as_xml, get_doctree_as_pyquery,
                 assert_issue_reference))


def pytest_configure(config):
    """
    Configure issue tracker tests.

    Adds ``confpy`` attribute to ``config`` which provides the path to the test
    ``conf.py`` file.
    """
    config.confpy = py.path.local(TEST_DIRECTORY).join('conf.py')


def pytest_funcarg__content(request):
    """
    The content for the test document as string.

    By default, the content is taken from the argument of the ``with_content``
    marker.  If no such marker exists, the content is build from the id
    returned by the ``issue_id`` funcargby prepending a dash before the id.
    The issue id ``'10'`` will thus produce the content ``'#10'``.  If the
    ``issue_id`` funcarg returns ``None``, a :exc:`~exceptions.ValueError` is
    raised eventually.

    Test modules may override this funcarg to add their own content.
    """
    content_mark = request.keywords.get('with_content')
    if content_mark:
        return content_mark.args[0]
    else:
        issue_id = request.getfuncargvalue('issue_id')
        if issue_id:
            return '#{0}'.format(issue_id)
    raise ValueError('no content provided')


def pytest_funcarg__srcdir(request):
    """
    The Sphinx source directory for the current test as path.

    This directory contains the standard test ``conf.py`` and a single document
    named ``index.rst``.  The content of this document is the return value of
    the ``content`` funcarg.
    """
    tmpdir = request.getfuncargvalue('tmpdir')
    srcdir = tmpdir.join('src')
    srcdir.ensure(dir=True)
    confpy = request.getfuncargvalue('pytestconfig').confpy
    confpy.copy(srcdir)
    content = request.getfuncargvalue('content')
    srcdir.join('index.rst').write(content)
    return srcdir


def pytest_funcarg__outdir(request):
    """
    The Sphinx output directory for the current test as path.
    """
    tmpdir = request.getfuncargvalue('tmpdir')
    return tmpdir.join('html')


def pytest_funcarg__doctreedir(request):
    """
    The Sphinx doctree directory for the current test as path.
    """
    tmpdir = request.getfuncargvalue('tmpdir')
    return tmpdir.join('doctrees')


def reset_global_state():
    """
    Remove global state setup by Sphinx.

    Makes sure that we got a fresh test application for each test.
    """
    SphinxStandaloneReader.transforms.remove(IssuesReferences)
    StandaloneHTMLBuilder.css_files.remove('_static/issuetracker.css')


def pytest_funcarg__confoverrides(request):
    """
    Configuration value overrides for the current test as dictionary.

    By default this funcarg takes the configuration overrides from the keyword
    arguments of the ``confoverrides`` marker.  If the marker doesn't exist,
    an empty dictionary is returned.

    Test modules may override this funcarg to return custom ``confoverrides``.
    """
    confoverrides_marker = request.keywords.get('confoverrides')
    return confoverrides_marker.kwargs if confoverrides_marker else {}


def pytest_funcarg__app(request):
    """
    A Sphinx application for testing.

    The app uses the source directory from the ``srcdir`` funcarg, and writes
    to the directories given by the ``outdir`` and ``doctreedir`` funcargs.
    Additional configuration values can be inserted into this application
    through the ``confoverrides`` funcarg.
    """
    srcdir = request.getfuncargvalue('srcdir')
    outdir = request.getfuncargvalue('outdir')
    doctreedir = request.getfuncargvalue('doctreedir')
    confoverrides = request.getfuncargvalue('confoverrides')
    app = Sphinx(str(srcdir), str(srcdir), str(outdir), str(doctreedir),
                 'html',confoverrides=confoverrides, status=None, warning=None,
                 freshenv=True)
    request.addfinalizer(reset_global_state)
    return app


def pytest_funcarg__issue(request):
    """
    An :class:`~sphinxcontrib.issuetracker.Issue` for the current test, or
    ``None``, if no issue is to be used.

    By default, this funcarg creates an issue from the arguments of the
    ``with_issue`` marker, or returns ``None``, if there is no such marker on
    the current test.

    Test modules may override this funcarg to provide their own issues for
    tests.
    """
    issue_marker = request.keywords.get('with_issue')
    if issue_marker:
        return Issue(*issue_marker.args, **issue_marker.kwargs)
    return None


def pytest_funcarg__issue_id(request):
    """
    The issue id for the current test, or ``None``, if no issue id is to be
    used.

    The issue id is taken from the ``id`` attribute of the issue returned by
    the ``issue`` funcarg.  If the ``issue`` funcarg returns ``None``, this
    funcarg also returns ``None``.
    """
    issue = request.getfuncargvalue('issue')
    if issue:
        return issue.id
    else:
        return None


def pytest_funcarg__mock_resolver(request):
    """
    A mocked callback for the ``issuetracker-resolve-issue`` event as
    :class:`~mock.Mock` object.

    The callback is already connected to the ``issuetracker-resolve-issue``
    event in the application provided by the ``app`` funcarg.  If the ``issue``
    funcarg is not ``None``, the callback will return this issue if the issue
    id given to the callback matches the id of this issue.  Otherwise it will
    always return ``None``.
    """
    lookup_mock_issue = Mock(name='lookup_mock_issue', return_value=None)
    issue = request.getfuncargvalue('issue')
    if issue:
        def lookup(app, tracker_config, issue_id):
            return issue if issue_id == issue.id else None
        lookup_mock_issue.side_effect = lookup
    app = request.getfuncargvalue('app')
    app.connect(b'issuetracker-resolve-issue', lookup_mock_issue)
    return lookup_mock_issue
