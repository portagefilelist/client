# standard library
import sys
import os
import pwd
from tempfile import mkstemp, mkdtemp
from time import time
import configparser
import argparse
from xml.sax.saxutils import escape
import tarfile

# external library
# portage api: sys-apps/portage
import portage
# http: dev-python/requests
import requests

VERSION = '3.x'
UPLOADURL='https://www.portagefilelist.de/data.php'
ALLOWED_REPOS = ['gentoo', 'guru']
HOME = os.path.expanduser("~")
# if it is run as cron and portage use. Otherwise use current user HOME
if pwd.getpwuid(os.getuid())[0] == 'portage':
    INFOFILE = '/var/lib/pfl/pfl.info'
else:
    INFOFILE = '%s/.pfl.info' % HOME

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
parser.add_argument('-r', '--repo', action='store', help='Update only for given repository: '+'|'.join(ALLOWED_REPOS))
parser.add_argument('-h', '--help', action='help', help='Show this help message and exit.')
parser.add_argument('-v', '--version', action='version', version='pfl ' + VERSION, help='Show version number and exit.')
args = parser.parse_args()

if args.pretend:
    print('Pretend mode. Data will be build and left to view. Nothing will be uploaded.')

_onlyRepo = ''
if args.repo:
    if args.repo in ALLOWED_REPOS:
        print('Collect data only from repository: "%s"' % args.repo)
        _onlyRepo = args.repo
    else:
        print('Invalid repo given. Valid values are: '+'|'.join(ALLOWED_REPOS))
        exit()

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

            if repo in ALLOWED_REPOS and mergedstamp >= since:
                if (_onlyRepo and repo != _onlyRepo):
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
            return None

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
                        print('working on (%d of %d) %s/%s-%s::%s' % (workingon, count, c, p, v, r))

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

        return categoryFiles

class PFL(object):
    _lastrun = 0
    _config = None

    def __init__(self):
        self._read_config()

    def _finish(self, xmlfiles, success = True):
        if success and not args.pretend:
            if not self._config.has_section('PFL'):
                self._config.add_section('PFL')

            self._config.set('PFL', 'lastrun', str(int(time())))
            self._config.set('PFL', 'version', VERSION)

            hconfig = open(INFOFILE, 'w')
            self._config.write(hconfig)
            hconfig.close()

        if xmlfiles and os.path.isdir(xmlfiles[0]):
            if args.pretend:
                print('Pretend mode. Keeping:\n'+'\n'.join(xmlfiles))
                print('The files need to be removed manually!')
            else:
                print('Cleanup ...')
                # the folder is the first element
                tmpDir = xmlfiles.pop(0)
                print(tmpDir + '*')
                for pathToBeRemoved in xmlfiles:
                    os.unlink(pathToBeRemoved)
                os.rmdir(tmpDir)
                print('Done.')

    def _read_config(self):
        self._config = configparser.ConfigParser()
        if os.path.isfile(INFOFILE):
            self._config.read(INFOFILE)

    def _last_run(self):
        if self._config.get('PFL', 'version', fallback='noversion') == 'noversion':
            return 0
        else:
            return int(self._config.get('PFL', 'lastrun', fallback=0))

    def run(self):
        pm = PortageMangle()

        xmlfiles = pm.collect_into_xml(self._last_run())

        if xmlfiles == None:
            print('Nothing to collect. If this is wrong, set PFL/lastrun in %s to 0' % INFOFILE)
            toClean = xmlfiles
        elif args.pretend:
            print('Pretend mode. Nothing to upload.')
            toClean = xmlfiles
        else:
            toClean = []
            tmpDir = xmlfiles.pop(0)
            toClean.append(tmpDir)

            print('Creating file to upload ...')
            fileToUpload = tmpDir + '.tar'
            tarFile = tarfile.open(fileToUpload, 'w')
            for toBeCompressed in xmlfiles:
                os.system('bzip2 %s' % toBeCompressed)
                fPath = toBeCompressed + '.bz2'
                tarFile.add(fPath, arcname=os.path.basename(fPath))
                toClean.append(fPath)
            tarFile.close()
            print('Done: %s' % fileToUpload)
            toClean.append(fileToUpload)

            try:
                print('uploading file %s to %s ...' % (fileToUpload, UPLOADURL))
                files = {'foo': open(fileToUpload, 'rb')}
                r = requests.post(UPLOADURL, files=files)
                print('HTTP Response Code: %d' % r.status_code)
                print('HTTP Response Body: %s' % r.text)
            except Exception as e:
                sys.stderr.write("%s\n" % e)
                self._finish(toClean, False)
                return

        self._finish(toClean, True)
