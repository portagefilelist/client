# portage api
import portage

# xml
from xml.sax.saxutils import escape

# http
import requests

import sys
import os
import pwd
from tempfile import mkstemp
from time import time
import configparser
import argparse

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/gpl-3.0.

VERSION = '3.3'
HOME = os.path.expanduser("~")
# if it is run as cron and portage use. Otherwise use current user HOME
if pwd.getpwuid(os.getuid())[0] == 'portage':
    INFOFILE = '/var/lib/pfl/pfl.info'
else:
    INFOFILE = '%s/.pfl.info' % HOME

UPLOADURL='https://www.portagefilelist.de/data.php'

parser = argparse.ArgumentParser(description='This is the PFL upload script. \
The purpose of this script is to collect the file names (not the content) of \
all installed packages from the Gentoo repo and upload them to \
portagefilelist.de. After some time your uploaded data will be imported into a \
searchable database. Thus you will provide a way for other people to find a \
package which contains a specific file/binary. Please visit \
https://www.portagefilelist.de for further information.', add_help=False)

parser.add_argument('-p', '--pretend', action='store_true', help='Collect data only and do not upload or change \
the last run value.')
parser.add_argument('-a', '--atom', action='store', help='Update only for given atom.')
parser.add_argument('-h', '--help', action='help', help='Show this help message and exit.')
parser.add_argument('-v', '--version', action='version', version='pfl ' + VERSION, help='Show version number and exit.')

args = parser.parse_args()

if args.pretend:
    print('Pretend mode. Data will be build and left to view. Nothing will be uploaded.')

# if only one specific package should be updated, check if the syntax is correct
# and a valid installed one
_onlyPackage = ''
if args.atom:
    if portage.dep.isvalidatom(args.atom) and portage.dep.isspecific(args.atom):
        _onlyPackage = portage.dep.dep_getcpv(args.atom)
    else:
        print('Invalid package atom provided. Use something like =category/package-1.23')
        exit()

# https://dev.gentoo.org/~zmedico/portage/doc/api/index.html
# https://wiki.gentoo.org/wiki/Project:Portage
class PortageMangle(object):
    _settings = None
    _vardbapi = None

    _xmlfile = None

    def __init__(self):
        eroot = portage.settings['EROOT']
        if eroot in portage.db:
            self._settings = portage.db[eroot]['vartree'].settings
            self._vardbapi = portage.db[eroot]['vartree'].dbapi
        else:
            raise Exception(f'Tree "{eroot}" not present.')

    def get_wellknown_cpvs(self, since):
        if _onlyPackage:
            if self._vardbapi.cpv_exists(_onlyPackage):
                # category, package, version of specific package
                c, p, v, r = portage.versions.catpkgsplit(_onlyPackage)
                cpvs = [c + '/' + p + '-' + v]
            else:
                print('No such atom installed.')
                return None
        else:
            # category, package, version of all installed packages
            cpvs = self._vardbapi.cpv_all()

        # search for pkgs from known repositories
        wellknown = {}
        wellknown_count = 0
        for cpv in cpvs:
            # category, package, version, revision
            c, p, v, r = portage.versions.catpkgsplit(cpv)
            if r != 'r0':
                v = '%s-%s' % (v, r)

            # repository
            repo, = self._vardbapi.aux_get(cpv, ['repository'])
            if len(repo) == 0:
                repo, = self._vardbapi.aux_get(cpv, ['REPOSITORY'])

            # timestamp of merge
            mergedstamp = self._vardbapi.aux_get(cpv, ['_mtime_'])[0]

            # add only if repo is gentoo. Maybe more in the future?
            if repo == 'gentoo' and mergedstamp >= since:
                wellknown.setdefault(c, {}).setdefault(p, []).append(v)
                wellknown_count = wellknown_count + 1

        return [wellknown_count, wellknown]

    def get_contents(self, c, p, v):
        dbl = portage.dblink(c, '%s-%s' % (p, v), self._settings['ROOT'], self._settings)
        return dbl.getcontents()

    def _write2file(self, txt, indent=None):
        if args.pretend and indent != None:
            os.write(self._xmlfile[0], bytes(indent, 'UTF-8'))

        os.write(self._xmlfile[0], bytes(txt, 'UTF-8'))

    def collect_into_xml(self, since):
        count, cpvs = self.get_wellknown_cpvs(since)

        # nothing to do
        if count == 0:
            return None

        self._xmlfile = mkstemp('.xml', 'pfl')

        print('writing xml file %s ...' % self._xmlfile[1])
        self._write2file('<?xml version="1.0" encoding="UTF-8"?>')
        self._write2file('<pfl xmlns="http://www.portagefilelist.de/xsd/collect">', '\n')

        workingon = 0
        for c in cpvs:
            self._write2file('<category name="%s">' % c, '\n\t')
            for p in cpvs[c]:
                for v in cpvs[c][p]:
                    workingon = workingon + 1
                    print('working on (%d of %d) %s/%s-%s' % (workingon, count, c, p, v))

                    contents = self.get_contents(c, p, v)

                    # no files -> this package does not matter
                    if len(contents) == 0:
                        continue

                    mergedstamp = self._vardbapi.aux_get('%s/%s-%s' % (c, p, v), ['_mtime_'])[0]

                    use = self._vardbapi.aux_get('%s/%s-%s' % (c, p, v), ['USE'])[0].split()
                    iuse = self._vardbapi.aux_get('%s/%s-%s' % (c, p, v), ['IUSE'])[0].split()
                    keywords = self._vardbapi.aux_get('%s/%s-%s' % (c, p, v), ['KEYWORDS'])[0].split()

                    us = []
                    arch = None

                    for u in use:
                        if u in iuse:
                            us.append(u)
                        if u in keywords or '~' + u in keywords:
                            arch = u
                    self._write2file('<package arch="%s" name="%s" timestamp="%s" version="%s">' % (arch, p, str(mergedstamp), v), '\n\t\t')

                    self._write2file('<files>', '\n\t\t\t')
                    for f in contents:
                        self._write2file('<file type="%s">%s</file>' % (contents[f][0], escape(f)), '\n\t\t\t\t')
                    self._write2file('</files>', '\n\t\t\t')

                    if len(us) > 0:
                        self._write2file('<uses>', '\n\t\t\t')
                        for u in us:
                            self._write2file('<use>%s</use>' %u, '\n\t\t\t\t')
                        self._write2file('</uses>', '\n\t\t\t')

                    self._write2file('</package>', '\n\t\t')

            self._write2file('</category>', '\n\t')
        self._write2file('</pfl>', '\n')

        os.close(self._xmlfile[0])

        return self._xmlfile[1]

class PFL(object):
    _lastrun = 0
    _config = None

    def __init__(self):
        self._read_config()

    def _finish(self, xmlfile, success = True):
        if success and not args.pretend:
            if not self._config.has_section('PFL'):
                self._config.add_section('PFL')

            self._config.set('PFL', 'lastrun', str(int(time())))
            self._config.set('PFL', 'version', VERSION)

            hconfig = open(INFOFILE, 'w')
            self._config.write(hconfig)
            hconfig.close()

        if xmlfile and os.path.isfile(xmlfile):
            if args.pretend:
                print('Pretend mode. Keeping %s' % xmlfile)
            else:
                print('deleting xml file %s ...' % xmlfile)
                os.unlink(xmlfile)
                print('Done.')

    def _read_config(self):
        self._config = configparser.ConfigParser()
        if os.path.isfile(INFOFILE):
            self._config.read(INFOFILE)

    def _last_run(self):
        if self._config.get('PFL', 'version', fallback='noversion') == 'noversion':
            return 0
        else:
            if self._config.get('PFL', 'version') != VERSION:
                print('new PFL version - I will collect all packages')
                return 0
            else:
                return int(self._config.get('PFL', 'lastrun', fallback=0))

    def run(self):
        pm = PortageMangle()

        xmlfile = pm.collect_into_xml(self._last_run())

        if xmlfile == None:
            print('nothing to collect. If this is wrong, set PFL/lastrun in %s to 0' % INFOFILE)
        elif args.pretend:
            print('Pretend mode. Nothing to upload.')
        else:
            curversion = None
            try:
                os.system('bzip2 %s' % xmlfile)
                xmlfile = xmlfile + '.bz2'
                print('uploading xml file %s to %s ...' % (xmlfile, UPLOADURL))
                files = {'foo': open(xmlfile, 'rb')}
                r = requests.post(UPLOADURL, files=files)

                print('HTTP Response Code: %d' % r.status_code)
                print('HTTP Response Body: %s' % r.text)
            except Exception as e:
                sys.stderr.write("%s\n" % e)
                self._finish(xmlfile, False)
                return

        self._finish(xmlfile, True)
