#!/bin/sh

keystr="${1}"

image="${2}"
archive="${3}"

if test "x${image}" != "x"; then
    imagebase="`basename "${image}"`"
    imagedir="`dirname "${image}"`"
    imagedirbase="`basename "${imagedir}"`"
fi

if test "x${archive}" = "x"; then
    container="${imagedir}"
else
    container="${archive}"
    archivebase="`basename "${archive}"`"
    archivedir="`dirname "${archive}"`"
    archivedirbase="`basename "${archivedir}"`"
fi

if test "x${container}" != "x"; then
    containerbase="`basename "${container}"`"
    containerdir="`dirname "${container}"`"
    containerdirbase="`basename "${containerdir}"`"
fi

rc=0

case "${keystr}" in
    'C-s')
        echo "image: ${image}"
        echo "imagebase: ${imagebase}"
        echo "imagedir: ${imagedir}"
        echo "imagedirbase: ${imagedirbase}"
        echo "archive: ${archive}"
        echo "archivebase: ${archivebase}"
        echo "archivedir: ${archivedir}"
        echo "archivedirbase: ${archivedirbase}"
        echo "container: ${container}"
        echo "containerbase: ${containerbase}"
        echo "containerdir: ${containerdir}"
        echo "containerdirbase: ${containerdirbase}"
        ;;
    *)
        echo "unknown key: ${keystr}"
        rc=1
        ;;
esac

exit ${rc}
