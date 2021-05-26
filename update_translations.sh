#!/bin/sh
ROOTDIR="mcomix/mcomix"
VERSION=`sed -nr "s%^VERSION = '([.0-9a-z]+)'$%\1%p" ${ROOTDIR}/constants.py`
MAINTAINER="NAME@HO.ST"

find ${ROOTDIR} -name '*.py' -exec \
     echo xgettext --sort-by-file --language=Python --output=mcomix.pot \
     --output-dir=${ROOTDIR}/messages/ --add-comments=TRANSLATORS \
     --from-code=utf-8 --package-name=MComix --package-version=${VERSION} \
     --msgid-bugs-address=${MAINTAINER} {} +

for pofile in ${ROOTDIR}/messages/*/LC_MESSAGES/*.po; do
    # Merge message files with master template, no fuzzy matching (-N)
    msgmerge -U --backup=none ${pofile} ${ROOTDIR}/messages/mcomix.pot
    # Compile translation, add "-f" to include fuzzy strings
    #msgfmt ${pofile} -o ${pofile%.*}.mo
done
