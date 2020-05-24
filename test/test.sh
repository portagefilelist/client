#!/bin/bash

source test.env
docker pull portagefilelist/pfl-base
docker run -it --rm -v "${PFL_DEV}:/pfl" -v "${PORTAGE}:/var/db/repos/gentoo" portagefilelist/pfl-base /bin/bash
