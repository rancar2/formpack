# coding: utf-8

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)

import json
import difflib

try:
    from cyordereddict import OrderedDict
except ImportError:
    from collections import OrderedDict

from .version import FormVersion
from .utils import get_version_identifiers, str_types
from .export import Export


class FormPack(object):

    # TODO: make a clear signature for __init__
    def __init__(self, versions, title='Submissions', id_string=None,
                 asset_type=None, submissions_xml=None):

        if not versions:
            raise ValueError('A FormPack must contain at least one FormVersion')

        self.versions = OrderedDict()
        self.id_string = id_string

        self.title = title

        self.asset_type = asset_type

        self.load_all_versions(versions)

        # QUESTION FOR ALEX: can you fix that ? I don't know how it works
        # nor what it's for. My guess is it should be outside of here,
        # in a separate tool, so that it export the same generator than
        # we use in build_fixture.py
        # if submissions_xml:
        #     self._load_submissions_xml(submissions_xml)

    def __repr__(self):
        return '<FormPack %s>' % self._stats()

    def lookup(self, prop, default=None):
        # can't use a one liner because sometimes self.prop is None
        result = getattr(self, prop, default)
        if result is None:
            return default
        return result

    def __getitem__(self, index):
        try:
            if isinstance(index, int):
                return tuple(self.versions.values())[index]
            else:
                return self.versions[index]
        except KeyError:
            raise KeyError('formpack with version [%s] not found' % str(index))
        except IndexError:
            raise IndexError('version at index %d is not available' % index)

    def _stats(self):
        _stats = OrderedDict()
        _stats['id_string'] = self.id_string
        _stats['versions'] = len(self.versions)
        # _stats['submissions'] = self.submissions_count()
        _stats['row_count'] = len(self[-1]._v.get('content', {})
                                             .get('survey', []))
        # returns stats in the format [ key="value" ]
        return '\n\t'.join(map(lambda key: '%s="%s"' % (
                            key, str(_stats[key])), _stats.keys()))

    def _load_submissions_xml(self, submissions):
        for submission_xml in submissions:
            (id_string, version_id) = get_version_identifiers(submission_xml)
            if version_id not in self.versions:
                raise KeyError('version [%s] is not available' % version_id)
            cur_ver = self.versions[version_id]
            cur_ver._load_submission_xml(submission_xml)

    def load_all_versions(self, versions):
        for schema in versions:
            self.load_version(schema)

    def load_version(self, schema):
        """ Load one version and attach it to this Formpack

            All the metadata parsing is delegated to the FormVersion class,
            hence several attributes for FormPack are populated on the fly
            while getting versions loaded:

                - title : the human readable name of the form. Match the one
                          from the most recent version.
                - id_string : the human readable id of the form. The same for
                              all versions of the same FormPack.

            Each version can be distinguish by its version_id, which is
            unique accross an entire FormPack. It can be None, but only for
            one version in the FormPack.
        """

        # TODO: make that an alternative constructor from_json_schema ?
        # this way we could get rid of the construct accepting a json schema
        # and pass it the choices, repeat and fieds
        form_version = FormVersion(self, schema)

        # NB: id_string are readable string unique to the form
        # while version id are id unique to one of the versions of the form

        # Avoid duplicate versions id
        if form_version.id in self.versions:
            if form_version.id is None:
                raise ValueError('cannot have two versions without '
                                 'a "version" id specified')

            raise ValueError('cannot have duplicate version id: %s'
                             % form_version.id)

        # If the form pack doesn't have an id_string, we get it from the
        # first form version. We also avoid heterogenenous id_string in versions
        if form_version.id_string:
            if self.id_string and self.id_string != form_version.id_string:
                raise ValueError('Versions must of the same form must '
                                 'share an id_string: %s != %s' % (
                                    self.id_string, form_version.id_string,
                                 ))

            self.id_string = form_version.id_string

        # If the form pack doesn't have an title, we get it from the
        # first form version.
        if form_version.title and not self.title:
            self.title = form_version.version_title

        self.versions[form_version.id] = form_version


    def version_diff(self, vn1, vn2):
        v1 = self.versions[vn1]
        v2 = self.versions[vn2]

        def summr(v):
            return json.dumps(v._v.get('content'),
                              indent=4,
                              sort_keys=True,
                              ).splitlines(1)
        out = []
        for line in difflib.unified_diff(summr(v1),
                                         summr(v2),
                                         fromfile="v%d" % vn1,
                                         tofile="v%d" % vn2,
                                         n=1):
            out.append(line)
        return ''.join(out)

    def to_dict(self, **kwargs):
        out = {
            u'versions': [v.to_dict() for v in self.versions.values()],
        }
        if self.title is not None:
            out[u'title'] = self.title
        if self.id_string is not None:
            out[u'id_string'] = self.id_string
        if self.asset_type is not None:
            out[u'asset_type'] = self.asset_type
        return out

    def to_json(self, **kwargs):
        return json.dumps(self.to_dict(), **kwargs)

    def export(self, header_lang=None, translation=None,
               group_sep=None, versions=-1):
        '''Create an export for a given version of the form '''

        if isinstance(versions, str_types + (int,)):
            versions = [versions]
        versions = [self[key] for key in versions]

        versions = OrderedDict((v.id, v) for v in versions)
        return Export(versions, header_lang=header_lang,
                      translation=translation, group_sep=group_sep,
                      title='submissions')

