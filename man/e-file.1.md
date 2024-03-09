% E-FILE(1) e-file user manual | Version 3.5.1

# NAME

e-file - Search which package does provide a file or command.

# SYNOPSIS

**e-file** *file*

**e-file** \[-h\] \[-v\]

# DESCRIPTION

This command searches on https://www.portagefilelist.de for the given
filename(slice.hpp) or path(/usr/include/exiv2/slice.hpp) and displays the
result with further information from local portage. Using * as a wildcard
(slice.\*) (/usr/include/exiv2/\*) works too.

The data is provided by the `pfl` command.

# USAGE

**e-file** \[-h\] \[-v\] *file*

# OPTIONS

`-h, --help`
:   Show this help message and exit.

`-v, --version`
:   Show version number and exit.

# EXIT STATUS

Nothing special yet.
A non-zero exit code is treated as an abnormal exit, and at times,
the error code indicates what the problem was.
A zero error code means a successful exit.

# EXAMPLES

Usual execution as a user: `e-file brctl` results in

```
*  app-shells/bash-completion
        Seen Versions:          2.11
        Portage Versions:       2.11 9999
        Repository:             Gentoo
        Homepage:               https://github.com/scop/bash-completion
        Description:            Programmable Completion for bash
        Matched Files:          /usr/share/bash-completion/completions/brctl/brctl

 *  net-misc/bridge-utils
        Seen Versions:          1.7.1-r1
        Portage Versions:       1.7.1-r1
        Repository:             Gentoo
        Homepage:               http://bridge.sourceforge.net/
        Description:            Tools for configuring the Linux kernel 802.1d Ethernet Bridge
        Matched Files:          /sbin/brctl/brctl
```

Wildcardsearch is also possible: `e-file apache2ct*`

```
[I] www-servers/apache
        Seen Versions:          2.2.29 2.4.34-r2 2.4.39 2.4.55-r1 2.4.57 2.4.57-r1
        Portage Versions:       2.4.57 2.4.57-r1
        Repository:             Gentoo
        Installed Versions:     2.4.57(Fri Jun 23 06:43:37 2023)
        Homepage:               https://httpd.apache.org/
        Description:            The Apache Web Server
        Matched Files:          /usr/sbin/apache2ctl/apache2ctl

 *  app-shells/bash-completion
        Seen Versions:          2.11
        Portage Versions:       2.11 9999
        Repository:             Gentoo
        Homepage:               https://github.com/scop/bash-completion
        Description:            Programmable Completion for bash
        Matched Files:          /usr/share/bash-completion/completions/apache2ctl/apache2ctl
```

# BUG REPORTS

Report to https://github.com/portagefilelist/client/issue

# COPYRIGHT

2023-2024 Banana mail@bananas-playground.net

?-2023 D. Buschke - Original creator

License: GNU General Public License v2 (GPLv2)

# SEE ALSO

pfl\(1\)

# VERSION

3.5.1
