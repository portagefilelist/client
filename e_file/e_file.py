import json
import argparse
from datetime import datetime

# external library
# portage api: sys-apps/portage
import portage
# dev-python/termcolor
from termcolor import colored
# http: dev-python/requests
import requests

VERSION = '3.x'
BASEURL = 'https://www.portagefilelist.de/query.php?file=%s'

def run(raw_args=None):
    parser = argparse.ArgumentParser(description='This script searches on \
https://www.portagefilelist.de for the given filename(slice.hpp) or \
path(/usr/include/exiv2/slice.hpp) and displays the result \
with further information from local portage. \
Using * as a wildcard (slice.*) (/usr/include/exiv2/*) works too.', add_help=False)

    parser.add_argument('-h', '--help', action='help', help='Show this help message and exit.')
    parser.add_argument('-v', '--version', action='version', version='e-file ' + VERSION)
    parser.add_argument('file', help='Filename or path to search for.')
    args = parser.parse_args(raw_args)

    out = ""
    try:
        r = requests.get(BASEURL % args.file)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        out = out + "An HTTP error occured\n"
        raise SystemExit(e)
    except requests.exceptions.ConnectionError as e:
        out = out + "An connection error occured\n"
        raise SystemExit(e)
    except requests.exceptions.Timeout as e:
        out = out + "Timeout\n"
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        out = out + "Something went totally wrong with the request\n"
        raise SystemExit(e)

    resultJson = json.loads(r.text)

    if 'error' in resultJson:
        out = out + resultJson['error']['code'] + "\n"
        out = out + resultJson['error']['message'] + "\n"
        return 1, out
    elif 'result' in resultJson:
        if len(resultJson['result']) > 0:
            cps = {}
            for file in resultJson['result']:
                category = file['category']
                package = file['package']
                version = file['version']
                filepath = file['path']
                repo = file['repository']

                if category not in cps:
                    cps[category] = {}

                if package not in cps[category]:
                    cps[category][package] = {
                            'versions': [version],
                            'files': [filepath]
                            }
                else:
                    cps[category][package]['versions'].append(version)
                    cps[category][package]['files'].append(filepath)

            eroot = portage.settings['EROOT']
            vardbapi = portage.db[eroot]['vartree'].dbapi
            portdbapi = portage.db[eroot]['porttree'].dbapi
            for category, packages in cps.items():
                for package, vf in packages.items():
                    installed_cpvs = sorted(set(vardbapi.cp_list('%s/%s' % (category, package))))
                    available_cpvs = sorted(set(portdbapi.cp_list('%s/%s' % (category, package))))

                    installed = False
                    if len(installed_cpvs) > 0:
                        installed = True

                    # *  category/package
                    # [I] category/package
                    if installed:
                        out = out + colored('[I] ', 'green')
                    else:
                        out = out + colored(' *  ', 'green')
                    out = out + f"{category}/{package}\n"

                    #        Seen Versions:          X.Y A.B
                    versions = sorted(set(vf['versions']))
                    out = out + colored('        Seen Versions:          %s\n' % ' '.join(versions), 'green')

                    #        Portage Versions:       X.Y A.B
                    out = out + colored('        Portage Versions:       ', 'green')
                    for available_cpv in available_cpvs:
                        out = out + colored('%s ' % portage.versions.cpv_getversion(available_cpv), 'green')
                    out = out + '\n'

                    #        Repository:             Name
                    out = out + colored('        Repository:             %s\n' % repo, 'green')

                    # old:
                    #        Last Installed Ver:     X.Y(Thu Apr 2 01:01:19 2020)
                    # new:
                    #        Installed Versions:     X.Y(Thu Apr 2 01:01:19 2020)
                    if installed:
                        out = out + colored('        Installed Versions:     ', 'green')
                        for installed_cpv in installed_cpvs:
                            build_time, = vardbapi.aux_get(installed_cpv, ['BUILD_TIME'])
                            try:
                                build_time = build_time = int(build_time.strip())
                            except ValueError:
                                build_time = 0

                            out = out + colored(portage.versions.cpv_getversion(installed_cpv), 'white', 'on_blue')
                            out = out + colored(datetime.fromtimestamp(build_time).strftime('(%c) '), 'magenta')

                        out = out + '\n'

                    if len(available_cpvs) > 0:
                        description, homepage = portdbapi.aux_get(available_cpvs[-1], ['DESCRIPTION', 'HOMEPAGE'])

                        #        Homepage:               http://example.org
                        out = out + colored('        Homepage:               ', 'green')
                        out = out + f"{homepage}\n"

                        #        Description:            package description
                        out = out + colored('        Description:            ', 'green')
                        out = out + f"{description}\n"

                    #        Matched Files:          /the/found/file; /another/found/file;
                    files = sorted(set(vf['files']))
                    out = out + colored('        Matched Files:          ', 'green')
                    out = out + f"{'; '.join(files)}\n"

                    out = out + '\n'
                    return 0, out

        else:
            out = out + 'Empty result return. This should not happend.\n'
            return 1, out
    else:
        out = out + 'Something went wrong with the request result.\n'
        out = out + resultJson
        return 1, out
