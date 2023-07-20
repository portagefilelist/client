# Portage File List Client
This are the client scripts used by Portage File List (PFL) to upload file names of installed Gentoo packages.
PFL allows users to search for files that are not installed on their system and figure out which ebuild they need to install in order to obtain it.

It also provides a tool for searching PFL from CLI (e-file).

## Install
`# emerge app-portage/pfl -av`

## Upload installed packages

### Why?
As Gentoo has a source code based package system you cannot predict the binary files created by a package.
Thus you might have trouble to find the package which provides a specific binary. E.g. the command `brctl` is
provided by the package `net-misc/bridge-utils`. [Try it](https://www.portagefilelist.de/index.php?fs=brctl&unique=1).

### How?
Just execute `pfl` or use the network-cron useflag which installs a weekly executed cronjob. 
