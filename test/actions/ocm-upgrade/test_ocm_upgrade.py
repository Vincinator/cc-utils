# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company and Gardener contributors
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest

# add the action directory so ocm_upgrade is importable
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '..', '..', '..', '.github', 'actions',
            'ocm-upgrade',
        )
    ),
)

import ocm
import ocm.gardener

import ocm_upgrade


def test_find_upgrade_vector_newer_available():
    cid = ocm.ComponentIdentity(
        name='example.com/comp',
        version='1.0.0',
    )

    vector = ocm.gardener.find_upgrade_vector(
        component_id=cid,
        version_lookup=lambda _: ['1.0.0', '1.1.0', '2.0.0'],
    )

    assert vector is not None
    assert vector.whence.version == '1.0.0'
    assert vector.whither.version == '2.0.0'


def test_find_upgrade_vector_already_latest():
    cid = ocm.ComponentIdentity(
        name='example.com/comp',
        version='2.0.0',
    )

    vector = ocm.gardener.find_upgrade_vector(
        component_id=cid,
        version_lookup=lambda _: ['1.0.0', '2.0.0'],
    )

    assert vector is None


def test_find_upgrade_vector_ignores_prerelease():
    cid = ocm.ComponentIdentity(
        name='example.com/comp',
        version='1.0.0',
    )

    vector = ocm.gardener.find_upgrade_vector(
        component_id=cid,
        version_lookup=lambda _: ['1.0.0', '1.1.0-dev'],
        ignore_prerelease_versions=True,
    )

    assert vector is None


def _make_cref(name, component_name, ver):
    return ocm.ComponentReference(
        name=name,
        componentName=component_name,
        version=ver,
    )


def test_upstream_duplicate_crefs_picks_greatest_version():
    '''
    Regression test: greatest_component_reference_version must return the
    greatest version across all refs matching a componentName, not the first.

    Mirrors the gardenlinux/landscape bug: upstream had 1877.14 listed before
    2150.2.0; the old first-match code would have returned 1877.14.
    '''
    gl_name = 'example.com/gardenlinux'
    crefs = [
        _make_cref('gardenlinux', gl_name, '1877.14'),  # comes first (old bug trigger)
        _make_cref('gardenlinux', gl_name, '2150.2.0'),
    ]

    result = ocm.gardener.greatest_component_reference_version(
        references=crefs,
        component_name=gl_name,
    )

    assert result == '2150.2.0'


def test_upstream_no_matching_cref_returns_none():
    crefs = [_make_cref('other', 'example.com/other', '1.0.0')]

    result = ocm.gardener.greatest_component_reference_version(
        references=crefs,
        component_name='example.com/gardenlinux',
    )

    assert result is None


def test_multi_major_component_names_detects_multiple_majors():
    refs = [
        _make_cref('gardenlinux-1877', 'example.com/gardenlinux', '1877.1.0'),
        _make_cref('gardenlinux-2150', 'example.com/gardenlinux', '2150.1.0'),
        _make_cref('foo', 'example.com/foo', '1.0.0'),
    ]

    result = ocm_upgrade._multi_major_component_names(refs)

    assert result == {'example.com/gardenlinux'}


def test_multi_major_component_names_single_major_excluded():
    # multiple references on the same major do not count as multi-major
    refs = [
        _make_cref('foo-a', 'example.com/foo', '1.0.0'),
        _make_cref('foo-b', 'example.com/foo', '1.2.0'),
    ]

    assert ocm_upgrade._multi_major_component_names(refs) == set()


def test_multi_major_component_names_empty_input():
    assert ocm_upgrade._multi_major_component_names([]) == set()
