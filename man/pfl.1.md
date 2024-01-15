% PFL(1) pfl user manual | Version 3.x

# NAME

pfl - Upload installed packages info since last run to PFL to make it searchable. 

# SYNOPSIS

**pfl** \[-p|--pretend\] \[-a *ATOM*|--atom *ATOM*\] \[-r *REPO*| --repo *REPO*\]

**pfl** \[-h\] \[-v\]

# DESCRIPTION

This is the PFL upload command. The purpose of this command is to collect the
file names (not the content) of all installed packages from the Gentoo and GURU repo
and upload them to portagefilelist.de. After some time your uploaded data will
be imported into a searchable database. Thus you will provide a way for other
people to find a package which contains a specific file/binary/command. 
Please visit https://www.portagefilelist.de for further information.

# USAGE

**pfl** \[-p\|-\-pretend] \[-a *ATOM*|-\-atom *ATOM*\] \[-r *REPO*| -\-repo *REPO*\] \[-h\] \[-v\]

# OPTIONS

`-a ATOM, --atom ATOM`
:   Update only for given atom.

`-p, --pretend`
:   Collect data only and do not upload or change the last run value.

`-r REPO, --repo REPO`
:   Update only for given repository: gentoo|guru

`-h, --help`
:   Show this help message and exit.

`-v, --version`
:   Show version number and exit.

# EXIT STATUS

Nothin special yet.
A non-zero exit code is treated as an abnormal exit, and at times, 
the error code indicates what the problem was. 
A zero error code means a successful exit.

# EXAMPLES

Usual execution as a user: `pfl`

Do not upload but create the upload files to be viewed: `pfl -p`

Update only for given repository. Values are gentoo or guru: `pfl -r guru`

Update only for a given package atom: `pfl -atom =media-fonts/fira-code-6.2`. 
Only the specific package atom syntax is currently supported. Like =media-fonts/fira-code-6.2 and NOT media-fonts/fira-code

# FILES

~/**.pfl.info**
:   Created after first run and stores current pfl version and last execution time.
    Execution time is used to gather only packages since last run.
    Remove file to reset last run time and gather all packages.

/var/lib/pfl/**pfl.info**
:   File used if run in system/cron context.
    Created after first run and stores current pfl version and last execution time.
    Execution time is used to gather only packages since last run.
    Remove file to reset last run time and gather all packages.


# BUG REPORTS

Report to https://github.com/portagefilelist/client/issue

# COPYRIGHT

2023-2024 Banana mail@bananas-playground.net

?-2023 D. Buschke - Original creator

License: GNU General Public License v2 (GPLv2)

# SEE ALSO

e-file\(1\)

# VERSION

3.x
