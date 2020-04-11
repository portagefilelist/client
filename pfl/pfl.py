# portage api
import portage

# xml
from xml.sax.saxutils import escape
import bz2

# http
import requests

import sys
import os
import io
import pwd
from tempfile import mkstemp
import configparser
from time import time
import argparse

# proxy
import re

VERSION = '3.0.2'
HOME = os.getenv('HOME')
DEBUG = os.path.exists(('%s/debugpfl' % HOME))
if pwd.getpwuid(os.getuid())[0] == 'portage':
    INFOFILE = '/var/lib/pfl/pfl.info'
else:
    INFOFILE = '%s/.pfl.info' % HOME;

UPLOADURL='https://upload.portagefilelist.de/data.php'

if DEBUG:
    import portage
    print('Portage Version: ', portage.VERSION)
    UPLOADURL=("%s?test" % UPLOADURL)


parser = argparse.ArgumentParser(description='This is the PFL upload script. \
The purpose of this script is to collect the file names (not the content) of \
all installed packages from the Gentoo repo and upload them to \
portagefilelist.de. After some time your uploaded data will be imported into a \
searchable database. Thus you will provide a way for other people to find a \
package which contains a specific file/binary. Please visit \
https://portagefilelist.de for further informations.', prog='pfl')

parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION)

args = parser.parse_args()

class PortageMangle(object):
    _settings = None
    _vardbapi = None

    _xmlfile = None

    def __init__(self):
        if '/' in portage.db:
            self._settings = portage.db['/']['vartree'].settings
            self._vardbapi = portage.db['/']['vartree'].dbapi
        else:
            raise Exception('Tree "/" not present.')

    def get_wellknown_cpvs(self, since):
        # category, package, version of all installed packages
        cpvs = self._vardbapi.cpv_all()

        # search for pkgs from known repositories
        wellknown = {}
        wellknown_count = 0
        for cpv in cpvs:
            c, p, v, r = portage.versions.catpkgsplit(cpv)
            if r != 'r0':
                v = '%s-%s' % (v, r)
                
            repo, = self._vardbapi.aux_get(cpv, ['repository'])
            if len(repo) == 0:
                repo, = self._vardbapi.aux_get(cpv, ['REPOSITORY'])

            # timestamp of merge
            mergedstamp = self._vardbapi.aux_get(cpv, ['_mtime_'])[0]

            if repo == 'gentoo' and mergedstamp >= since:
                wellknown.setdefault(c, {}).setdefault(p, []).append(v)
                wellknown_count = wellknown_count + 1
                
        return [wellknown_count, wellknown]

    def get_contents(self, c, p, v):
        dbl = portage.dblink(c, '%s-%s' % (p, v), self._settings['ROOT'], self._settings)
        return dbl.getcontents()

    def _write2file(self, txt, indent=None):
        if DEBUG and indent != None:
            os.write(self._xmlfile[0], bytes(indent, 'UTF-8'))

        os.write(self._xmlfile[0], bytes(txt, 'UTF-8'))

    def collect_into_xml(self, since):
        self._xmlfile = mkstemp('.xml', 'pfl')

        count, cpvs = self.get_wellknown_cpvs(since)
        
        # nothing to do
        if count == 0:
            return None
        
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
        if success:
            if not self._config.has_section('PFL'):
                self._config.add_section('PFL')

            if DEBUG:
                self._config.set('PFL', 'lastrun', '0')
            else:
                self._config.set('PFL', 'lastrun', str(int(time())))
            self._config.set('PFL', 'version', VERSION)
            
            hconfig = open(INFOFILE, 'w')
            self._config.write(hconfig)
            hconfig.close()
            
        if xmlfile and os.path.isfile(xmlfile):
            if DEBUG:
                print('manually check xml file %s' % xmlfile);
            else:
                print('deleting xml file %s ...' % xmlfile)
                os.unlink(xmlfile)
        
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
                if DEBUG:
                    return 0
                else:
                    return int(self._config.get('PFL', 'lastrun', fallback=0))

    def run(self):
        pm = PortageMangle()
        
        xmlfile = pm.collect_into_xml(self._last_run())

        if xmlfile == None:
            print('nothing to collect. If this is wrong, set PFL/lastrun in %s to 0' % INFOFILE)
        else:
            curversion = None
            try:
                os.system('bzip2 %s' % xmlfile)
                xmlfile = xmlfile + '.bz2'
                print('uploading xml file %s to %s ...' % (xmlfile, UPLOADURL))
                files = {'foo': open(xmlfile, 'rb')}
                r = requests.post(UPLOADURL, files=files)

                if DEBUG and r != None:
                    print('HTTP Response Code: %d' % r.status_code);
                    print('HTTP Response Body:\n%s' % r.text);
            except Exception as e:
                sys.stderr.write("%s\n" % e)
                self._finish(xmlfile, False)
                return

        self._finish(xmlfile, True)