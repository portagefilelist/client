# Copyright 2024 Banana and contributors of https://github.com/portagefilelist
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# standard library
import sys
import os
import pwd
from tempfile import mkstemp, mkdtemp
from time import time
import configparser
from xml.sax.saxutils import escape
import tarfile

# external library
# portage api: sys-apps/portage
import portage
# http: dev-python/requests
import requests

VERSION = '3.x.x'
UPLOADURL='https://www.portagefilelist.de/data.php'
ALLOWED_REPOS = ['gentoo', 'guru']

# if it is run as cron and portage use. Otherwise use current user HOME
if pwd.getpwuid(os.getuid())[0] == 'portage':
    INFOFILE = '/var/lib/pfl/pfl.info'
else:
    HOME = os.path.expanduser("~")
    INFOFILE = '%s/.pfl.info' % HOME

# the main method to run this.
# options are
# options = {
#      'onlyRepo': '',
#      'onlyPackage': '',
#      'pretend': args.pretend,
#      'stdout': False
#  }
# Use options['stdout'] = True if you want to run this as a script which prints the output as it happens.
# With False the output is collected and returned, so no immediate display what is going on.
def run(options):
    start = PFL(options)
    return start.run()

# https://dev.gentoo.org/~zmedico/portage/doc/api/index.html
# https://wiki.gentoo.org/wiki/Project:Portage
class PortageMangle(object):
    _settings = None
    _vardbapi = None
    _options = None
    _out = ''

    def __init__(self, options):
        self._options = options
        eroot = portage.settings['EROOT']
        if eroot in portage.db:
            self._settings = portage.db[eroot]['vartree'].settings
            self._vardbapi = portage.db[eroot]['vartree'].dbapi
        else:
            raise Exception(f'Tree "{eroot}" not present.')

    def log(self, output):
        if self._options['stdout']:
            print(output)
        else:
            self._out += output + '\n'

    def get_wellknown_cpvs(self, since):
        if self._options['onlyPackage']:
            if self._vardbapi.cpv_exists(self._options['onlyPackage']):
                # category, package, version of specific package
                c, p, v, r = portage.versions.catpkgsplit(self._options['onlyPackage'])
                if r != 'r0':
                    v = '%s-%s' % (v, r)
                cpvs = [c + '/' + p + '-' + v]
            else:
                self.log('No such atom installed.')
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

            if repo in ALLOWED_REPOS and mergedstamp >= since:
                if self._options['onlyRepo'] and repo != self._options['onlyRepo']:
                    continue

                wellknown.setdefault(repo, {}).setdefault(c, {}).setdefault(p, []).append(v)
                wellknown_count = wellknown_count + 1

        return [wellknown_count, wellknown]

    def get_contents(self, c, p, v):
        dbl = portage.dblink(c, '%s-%s' % (p, v), self._settings['ROOT'], self._settings)
        return dbl.getcontents()

    def _write2file(self, file, txt, indent):
        os.write(file[0], bytes(indent + txt, 'UTF-8'))

    # create a xml file per category and return a list of created xml files
    def collect_into_xml(self, since):
        count, cpvs = self.get_wellknown_cpvs(since)

        # nothing to do
        if count == 0:
            return None, self._out

        # first is the temp dir the files are stored in
        categoryFiles = []
        categoryFiles.append(mkdtemp(None, 'pfl-'))

        workingon = 0
        for r in cpvs: # repository
            for c in cpvs[r]: # category
                # https://docs.python.org/3/library/tempfile.html#tempfile.mkstemp
                categoryFile = mkstemp('.xml', 'pfl-', categoryFiles[0])
                self._write2file(categoryFile, '<?xml version="1.0" encoding="UTF-8"?>', '')
                self._write2file(categoryFile, '<pfl xmlns="http://www.portagefilelist.de/xsd/collect">', '\n')
                self._write2file(categoryFile, '<category name="%s">' % c, '\n\t')
                categoryFiles.append(categoryFile[1])

                for p in cpvs[r][c]: # packages
                    for v in cpvs[r][c][p]: # versions
                        workingon = workingon + 1
                        self.log('working on (%d of %d) %s/%s-%s::%s' % (workingon, count, c, p, v, r))

                        contents = self.get_contents(c, p, v)

                        # no files -> this package does not matter
                        if len(contents) == 0:
                            continue

                        mergedstamp = self._vardbapi.aux_get('%s/%s-%s' % (c, p, v), ['_mtime_'])[0]

                        use = self._vardbapi.aux_get('%s/%s-%s' % (c, p, v), ['USE'])[0].split()
                        iuse = self._vardbapi.aux_get('%s/%s-%s' % (c, p, v), ['IUSE'])[0].split()
                        keywords = self._vardbapi.aux_get('%s/%s-%s' % (c, p, v), ['KEYWORDS'])[0].split()

                        us = []
                        arch = 'none'

                        for u in use:
                            if u in iuse:
                                us.append(u)
                            if u in keywords or '~' + u in keywords:
                                arch = u
                        self._write2file(categoryFile, '<package arch="%s" name="%s" timestamp="%s" version="%s" repo="%s">' % (arch, p, str(mergedstamp), v, r), '\n\t\t')

                        self._write2file(categoryFile, '<files>', '\n\t\t\t')
                        for f in contents:
                            self._write2file(categoryFile, '<file type="%s">%s</file>' % (contents[f][0], escape(f)), '\n\t\t\t\t')
                        self._write2file(categoryFile, '</files>', '\n\t\t\t')

                        if len(us) > 0:
                            self._write2file(categoryFile, '<uses>', '\n\t\t\t')
                            for u in us:
                                self._write2file(categoryFile, '<use>%s</use>' %u, '\n\t\t\t\t')
                            self._write2file(categoryFile, '</uses>', '\n\t\t\t')

                        self._write2file(categoryFile, '</package>', '\n\t\t')
                self._write2file(categoryFile, '</category>', '\n\t')
                self._write2file(categoryFile, '</pfl>', '\n')
                os.close(categoryFile[0])

        return categoryFiles, self._out


class PFL(object):
    _lastrun = 0
    _config = None
    _options = None
    _out = ''

    def __init__(self, options):
        self._options = options
        self._read_config()

    def _finish(self, xmlfiles, success = True):
        if success and not self._options['pretend']:
            if not self._config.has_section('PFL'):
                self._config.add_section('PFL')

            self._config.set('PFL', 'lastrun', str(int(time())))
            self._config.set('PFL', 'version', VERSION)

            hconfig = open(INFOFILE, 'w')
            self._config.write(hconfig)
            hconfig.close()

        if xmlfiles and os.path.isdir(xmlfiles[0]):
            if self._options['pretend']:
                self.log('Pretend mode. Keeping:\n'+'\n'.join(xmlfiles))
                self.log('The files need to be removed manually!')
            else:
                self.log('Cleanup ...')
                # the folder is the first element
                tmpDir = xmlfiles.pop(0)
                self.log(tmpDir + '*')
                for pathToBeRemoved in xmlfiles:
                    os.unlink(pathToBeRemoved)
                os.rmdir(tmpDir)
                self.log('Done.')

    def _read_config(self):
        self._config = configparser.ConfigParser()
        if os.path.isfile(INFOFILE):
            self._config.read(INFOFILE)

    def _last_run(self):
        if self._config.get('PFL', 'version', fallback='noversion') == 'noversion':
            return 0
        else:
            return int(self._config.get('PFL', 'lastrun', fallback=0))

    def log(self, output):
        if self._options['stdout']:
            print(output)
        else:
            self._out += output + '\n'

    def run(self):
        pm = PortageMangle(self._options)

        xmlfiles, msg = pm.collect_into_xml(self._last_run())
        self.log(msg)

        if xmlfiles == None:
            self.log('Nothing to collect. If this is wrong, set PFL/lastrun in {} to 0'.format(INFOFILE))
            toClean = xmlfiles
        elif self._options['pretend']:
            self.log('Pretend mode. Nothing to upload.')
            toClean = xmlfiles
        else:
            toClean = []
            tmpDir = xmlfiles.pop(0)
            toClean.append(tmpDir)

            self.log('Creating file to upload ...')
            fileToUpload = tmpDir + '.tar'
            tarFile = tarfile.open(fileToUpload, 'w')
            for toBeCompressed in xmlfiles:
                os.system('bzip2 %s' % toBeCompressed)
                fPath = toBeCompressed + '.bz2'
                tarFile.add(fPath, arcname=os.path.basename(fPath))
                toClean.append(fPath)
            tarFile.close()
            self.log('Done: {}'.format(fileToUpload))
            toClean.append(fileToUpload)

            try:
                self.log('uploading file {} to {} ...'.format(fileToUpload, UPLOADURL))
                files = {'foo': open(fileToUpload, 'rb')}
                r = requests.post(UPLOADURL, files=files)
                self.log('HTTP Response Code: {}'.format(r.status_code))
                self.log('HTTP Response Body: {}'.format(r.text))
            except Exception as e:
                sys.stderr.write("%s\n" % e)
                self._finish(toClean, False)
                return 1, self._out

        self._finish(toClean, True)
        return 0, self._out
