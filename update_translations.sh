#!/bin/sh
ROOTDIR="mcomix/mcomix"
VERSION=$(grep VERSION $ROOTDIR/constants.py | sed -e "s/VERSION = //" -e "s/'//g")
MAINTAINER="NAME@HO.ST"

xgettext -LPython -omcomix.pot -p$ROOTDIR/messages/ -cTRANSLATORS \
    --from-code=utf-8 --package-name=MComix --package-version=${VERSION} \
    --msgid-bugs-address=${MAINTAINER} \
    $ROOTDIR/*.py $ROOTDIR/archive/*.py $ROOTDIR/library/*.py

for pofile in $ROOTDIR/messages/*/LC_MESSAGES/*.po
do
    # Merge message files with master template, no fuzzy matching (-N)
    msgmerge -U --backup=none ${pofile} $ROOTDIR/messages/mcomix.pot
    # Compile translation, add "-f" to include fuzzy strings
    #msgfmt ${pofile} -o ${pofile%.*}.mo
done
