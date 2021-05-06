#!/bin/sh

keystr="${1}"
imagepath="${2}"
archivepath="${3}"
rc=1

case "${keystr}" in
    'C-s')
        echo 'imagepath:' "${imagepath}"
        echo 'archivepath:' "${archivepath}"
        rc=0
        ;;
    *)
        echo "unknown key: ${keystr}"
        ;;
esac

exit ${rc}
