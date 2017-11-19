"""thumbnail.py - Thumbnail module for MComix implementing (most of) the
freedesktop.org "standard" at http://jens.triq.net/thumbnail-spec/
"""

import os
import re
import shutil
import tempfile
import mimetypes
import threading
import itertools
import traceback
import PIL.Image as Image
from urllib.request import pathname2url

from hashlib import md5

from mcomix.preferences import prefs
from mcomix import archive_extractor
from mcomix import constants
from mcomix import archive_tools
from mcomix import tools
from mcomix import image_tools
from mcomix import portability
from mcomix import i18n
from mcomix import callback
from mcomix import log


class Thumbnailer(object):
    """ The Thumbnailer class is responsible for managing MComix
    internal thumbnail creation. Depending on its settings,
    it either stores thumbnails on disk and retrieves them later,
    or simply creates new thumbnails each time it is called. """

    def __init__(self, dst_dir=constants.THUMBNAIL_PATH, store_on_disk=None,
                 size=None, force_recreation=False, archive_support=False):
        """
        <dst_dir> set the thumbnailer's storage directory.

        If <store_on_disk> on disk is True, it changes the thumbnailer's
        behaviour to store files on disk, or just create new thumbnails each
        time it was called when set to False. Defaults to the 'create
        thumbnails' preference if not set.

        The dimensions for the created thumbnails is set by <size>, a (width,
        height) tupple. Defaults to the 'thumbnail size' preference if not set.

        If <force_recreation> is True, thumbnails stored on disk
        will always be re-created instead of being re-used.

        If <archive_support> is True, support for archive thumbnail creation
        (based on cover detection) is enabled. Otherwise, only image files are
        supported.
        """
        self.dst_dir = dst_dir
        if store_on_disk is None:
            self.store_on_disk = prefs['create thumbnails']
        else:
            self.store_on_disk = store_on_disk
        if size is None:
            self.width = self.height = prefs['thumbnail size']
            self.default_sizes = True
        else:
            self.width, self.height = size
            self.default_sizes = False
        self.force_recreation = force_recreation
        self.archive_support = archive_support

    def thumbnail(self, filepath, async=False):
        """ Returns a thumbnail pixbuf for <filepath>, transparently handling
        both normal image files and archives. If a thumbnail file already exists,
        it is re-used. Otherwise, a new thumbnail is created from <filepath>.

        Returns None if thumbnail creation failed, or if the thumbnail creation
        is run asynchrounosly. """

        # Update width and height from preferences if they haven't been set explicitly
        if self.default_sizes:
            self.width = prefs['thumbnail size']
            self.height = prefs['thumbnail size']

        if self._thumbnail_exists(filepath):
            thumbpath = self._path_to_thumbpath(filepath)
            pixbuf = image_tools.load_pixbuf(thumbpath)
            self.thumbnail_finished(filepath, pixbuf)
            return pixbuf

        else:
            if async:
                thread = threading.Thread(target=self._create_thumbnail, args=(filepath,))
                thread.name += '-thumbnailer'
                thread.setDaemon(True)
                thread.start()
                return None
            else:
                return self._create_thumbnail(filepath)

    @callback.Callback
    def thumbnail_finished(self, filepath, pixbuf):
        """ Called every time a thumbnail has been completed.
        <filepath> is the file that was used as source, <pixbuf> is the
        resulting thumbnail. """

        pass

    def delete(self, filepath):
        """ Deletes the thumbnail for <filepath> (if it exists) """
        thumbpath = self._path_to_thumbpath(filepath)
        if os.path.isfile(thumbpath):
            try:
                os.remove(thumbpath)
            except IOError as error:
                log.error(_("! Could not remove file \"%s\""), thumbpath)
                log.error(error)

    def _create_thumbnail_pixbuf(self, filepath):
        """ Creates a thumbnail pixbuf from <filepath>, and returns it as a
        tuple along with a file metadata dictionary: (pixbuf, tEXt_data) """

        if self.archive_support:
            mime = archive_tools.archive_mime_type(filepath)
        else:
            mime = None
        if mime is not None:
            cleanup = []
            try:
                tmpdir = tempfile.mkdtemp(prefix=u'mcomix_archive_thumb.')
                cleanup.append(lambda: shutil.rmtree(tmpdir, True))
                archive = archive_tools.get_recursive_archive_handler(filepath,
                                                                      tmpdir,
                                                                      type=mime)
                if archive is None:
                    return None, None
                cleanup.append(archive.close)
                files = archive.list_contents()
                wanted = self._guess_cover(files)
                if wanted is None:
                    return None, None

                archive.extract(wanted, tmpdir)

                image_path = os.path.join(tmpdir, wanted)
                if not os.path.isfile(image_path):
                    return None, None

                pixbuf = image_tools.load_pixbuf_size(image_path, self.width, self.height)
                if self.store_on_disk:
                    tEXt_data = self._get_text_data(image_path)
                    # Use the archive's mTime instead of the extracted file's mtime
                    tEXt_data['tEXt::Thumb::MTime'] = str(os.stat(filepath).st_mtime)
                else:
                    tEXt_data = None

                return pixbuf, tEXt_data
            finally:
                for fn in reversed(cleanup):
                    fn()

        elif image_tools.is_image_file(filepath):
            pixbuf = image_tools.load_pixbuf_size(filepath, self.width, self.height)
            if self.store_on_disk:
                tEXt_data = self._get_text_data(filepath)
            else:
                tEXt_data = None

            return pixbuf, tEXt_data
        else:
            return None, None

    def _create_thumbnail(self, filepath):
        """ Creates the thumbnail pixbuf for <filepath>, and saves the pixbuf
        to disk if necessary. Returns the created pixbuf, or None, if creation failed. """

        pixbuf, tEXt_data = self._create_thumbnail_pixbuf(filepath)
        self.thumbnail_finished(filepath, pixbuf)

        if pixbuf and self.store_on_disk:
            thumbpath = self._path_to_thumbpath(filepath)
            self._save_thumbnail(pixbuf, thumbpath, tEXt_data)

        return pixbuf

    def _get_text_data(self, filepath):
        """ Creates a tEXt dictionary for <filepath>. """
        mime = mimetypes.guess_type(filepath)[0] or "unknown/mime"
        uri = portability.uri_prefix() + pathname2url(i18n.to_utf8(os.path.normpath(filepath)))
        stat = os.stat(filepath)
        # MTime could be floating point number, so convert to long first to have a fixed point number
        mtime = str(stat.st_mtime)
        size = str(stat.st_size)
        format, width, height = image_tools.get_image_info(filepath)
        return {
            'tEXt::Thumb::URI':           uri,
            'tEXt::Thumb::MTime':         mtime,
            'tEXt::Thumb::Size':          size,
            'tEXt::Thumb::Mimetype':      mime,
            'tEXt::Thumb::Image::Width':  str(width),
            'tEXt::Thumb::Image::Height': str(height),
            'tEXt::Software':             'MComix %s' % constants.VERSION
        }

    def _save_thumbnail(self, pixbuf, thumbpath, tEXt_data):
        """ Saves <pixbuf> as <thumbpath>, with additional metadata
        from <tEXt_data>. If <thumbpath> already exists, it is overwritten. """

        try:
            directory = os.path.dirname(thumbpath)
            if not os.path.isdir(directory):
                os.makedirs(directory, 0o700)
            if os.path.isfile(thumbpath):
                os.remove(thumbpath)

            option_keys = []
            option_values = []
            for key, value in tEXt_data.items():
                option_keys.append(key)
                option_values.append(value)
            pixbuf.savev(thumbpath, 'png', option_keys, option_values)
            os.chmod(thumbpath, 0o600)

        except Exception as ex:
            log.warning( _('! Could not save thumbnail "%(thumbpath)s": %(error)s'),
                { 'thumbpath' : thumbpath, 'error' : ex } )

    def _thumbnail_exists(self, filepath):
        """ Checks if the thumbnail for <filepath> already exists.
        This function will return False if the thumbnail exists
        and it's mTime doesn't match the mTime of <filepath>,
        it's size is different from the one specified in the thumbnailer,
        or if <force_recreation> is True. """

        if not self.force_recreation:
            thumbpath = self._path_to_thumbpath(filepath)

            if os.path.isfile(thumbpath):
                # Check the thumbnail's stored mTime
                try:
                    img = Image.open(thumbpath)
                except IOError:
                    return False

                info = img.info
                stored_mtime = info['Thumb::MTime']
                # The source file might no longer exist
                file_mtime = os.path.isfile(filepath) and os.stat(filepath).st_mtime or stored_mtime
                return stored_mtime == file_mtime and \
                    max(*img.size) == max(self.width, self.height)
            else:
                return False
        else:
            return False

    def _path_to_thumbpath(self, filepath):
        """ Converts <path> to an URI for the thumbnail in <dst_dir>. """
        uri = portability.uri_prefix() + pathname2url(i18n.to_utf8(os.path.normpath(filepath)))
        return self._uri_to_thumbpath(uri)

    def _uri_to_thumbpath(self, uri):
        """ Return the full path to the thumbnail for <uri> with <dst_dir>
        being the base thumbnail directory. """
        md5hash = md5(uri.encode()).hexdigest()
        thumbpath = os.path.join(self.dst_dir, md5hash + '.png')
        return thumbpath

    def _guess_cover(self, files):
        """Return the filename within <files> that is the most likely to be the
        cover of an archive using some simple heuristics.
        """
        # Ignore MacOSX meta files.
        files = itertools.ifilter(lambda filename:
                u'__MACOSX' not in os.path.normpath(filename).split(os.sep),
                files)
        # Ignore credit files if possible.
        files = itertools.ifilter(lambda filename:
                u'credit' not in os.path.split(filename)[1].lower(), files)

        images = list(itertools.ifilter(image_tools.SUPPORTED_IMAGE_REGEX.search, files))

        tools.alphanumeric_sort(images)

        front_re = re.compile('(cover|front)', re.I)
        candidates = filter(front_re.search, images)
        candidates = [c for c in candidates if 'back' not in c.lower()]

        if candidates:
            return candidates[0]

        if images:
            return images[0]

        return None

# vim: expandtab:sw=4:ts=4
