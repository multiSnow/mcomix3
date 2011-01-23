# -*- coding: utf-8 -*-

""" Glue around libunrar.so/unrar.dll to extract RAR files without having to
resort to calling rar/unrar manually. """

import sys, os
import ctypes, ctypes.util

from mcomix import constants

class UnrarDll(object):
    """ Wrapper class for libunrar. All string values passed to this class must be unicode objects.
    In turn, all values returned are also unicode. """

    class _OpenMode:
        """ Rar open mode """
        RAR_OM_LIST    = 0
        RAR_OM_EXTRACT = 1

    class _ProcessingMode:
        """ Rar file processing mode """
        RAR_SKIP       = 0
        RAR_EXTRACT    = 2

    class _ErrorCode:
        """ Rar error codes """
        ERAR_END_ARCHIVE = 10
        ERAR_NO_MEMORY = 11
        ERAR_BAD_DATA = 12
        ERAR_BAD_ARCHIVE = 13
        ERAR_UNKNOWN_FORMAT = 14
        ERAR_EOPEN = 15
        ERAR_ECREATE = 16
        ERAR_ECLOSE = 17
        ERAR_EREAD = 18
        ERAR_EWRITE = 19
        ERAR_SMALL_BUF = 20
        ERAR_UNKNOWN = 21
        ERAR_MISSING_PASSWORD = 22

    class _RAROpenArchiveDataEx(ctypes.Structure):
        """ Archive header structure. Used by DLL calls. """
        _fields_ = [("ArcName", ctypes.c_char_p),
                      ("ArcNameW", ctypes.c_wchar_p),
                      ("OpenMode", ctypes.c_uint),
                      ("OpenResult", ctypes.c_uint),
                      ("CmtBuf", ctypes.c_char_p),
                      ("CmtSize", ctypes.c_uint),
                      ("CmtState", ctypes.c_uint),
                      ("Flags", ctypes.c_uint),
                      ("Reserved", ctypes.c_uint * 32)]

    class _RARHeaderDataEx(ctypes.Structure):
        """ Archive file structure. Used by DLL calls. """
        _fields_ = [("ArcName", ctypes.c_char * 1024),
                      ("ArcNameW", ctypes.c_wchar * 1024),
                      ("FileName", ctypes.c_char * 1024),
                      ("FileNameW", ctypes.c_wchar * 1024),
                      ("Flags", ctypes.c_uint),
                      ("PackSize", ctypes.c_uint),
                      ("PackSizeHigh", ctypes.c_uint),
                      ("UnpSize", ctypes.c_uint),
                      ("UnpSizeHigh", ctypes.c_uint),
                      ("HostOS", ctypes.c_uint),
                      ("FileCRC", ctypes.c_uint),
                      ("FileTime", ctypes.c_uint),
                      ("UnpVer", ctypes.c_uint),
                      ("Method", ctypes.c_uint),
                      ("FileAttr", ctypes.c_uint),
                      ("CmtBuf", ctypes.c_char_p),
                      ("CmtBufSize", ctypes.c_uint),
                      ("CmtSize", ctypes.c_uint),
                      ("CmtState", ctypes.c_uint),
                      ("Reserved", ctypes.c_uint * 1024)]


    @staticmethod
    def is_available():
        """ Returns True if unrar.dll can be found, False otherwise. """
        return bool(_get_unrar_dll())

    def __init__(self, archive):
        """ Initialize Unrar.dll. """
        assert isinstance(archive, unicode), "Archive must be Unicode string"
        self._unrar = _get_unrar_dll()
        self._archive = archive
        self._handle = None
        self._callback_function = None

        # Set up function prototypes
        self._unrar.RAROpenArchiveEx.restype = ctypes.c_void_p
        self._unrar.RARCloseArchive.restype = ctypes.c_int
        self._unrar.RARReadHeaderEx.restype = ctypes.c_int
        self._unrar.RARProcessFileW.restype = ctypes.c_int

    def list_contents(self):
        """ Returns a list of files in the archive. """

        # Obtain handle for RAR file, opening it in LIST mode
        handle = self._open(self._archive, UnrarDll._OpenMode.RAR_OM_LIST)
        # Information about the current file will be stored in this structure
        headerdata = UnrarDll._RARHeaderDataEx()
        filelist = []

        # Read first header
        result = self._unrar.RARReadHeaderEx(handle, ctypes.byref(headerdata))
        while result == 0:
            filelist.append(headerdata.FileNameW)
            # Skip to the next entry
            self._unrar.RARProcessFileW(handle, UnrarDll._ProcessingMode.RAR_SKIP, None, None)
            # Read it's header
            result = self._unrar.RARReadHeaderEx(handle, ctypes.byref(headerdata))

        self._close(handle)

        return filelist

    def extract(self, filename, destination_path, try_again=True):
        """ Extract <filename> from the archive to <destination_path>.
        This path should include the full filename. """
        # Obtain handle for RAR file, opening it in EXTRACT mode
        if not self._handle:
            handle = self._handle = self._open(self._archive, UnrarDll._OpenMode.RAR_OM_EXTRACT)
        else:
            handle = self._handle

        # Information about the current file will be stored in this structure
        headerdata = UnrarDll._RARHeaderDataEx()

        # Read first header
        errorcode = self._unrar.RARReadHeaderEx(handle, ctypes.byref(headerdata))
        while errorcode == 0:
            # Check if the current file matches the requested file
            if (headerdata.FileNameW == filename):
                # Extract file and stop processing
                result = self._unrar.RARProcessFileW(handle,
                    UnrarDll._ProcessingMode.RAR_EXTRACT, None,
                    ctypes.c_wchar_p(destination_path))
                if result != 0:
                    # Close archive
                    self.close()
                    errormessage = UnrarException.get_error_message(result)
                    raise UnrarException("Couldn't extract file: %s" % errormessage)

                break
            else:
                # Skip to the next entry
                self._unrar.RARProcessFileW(handle, UnrarDll._ProcessingMode.RAR_SKIP, None, None)
                # Read it's header
                errorcode = self._unrar.RARReadHeaderEx(handle, ctypes.byref(headerdata))

        # Archive end was reached, this might be due to out-of-order extraction
        # while the handle was still open.
        if errorcode == UnrarDll._ErrorCode.ERAR_END_ARCHIVE:
            # Close the archive and jump back to archive start and try to extract file again.
            # Do this only once; if the file isn't found after a second full pass,
            # it probably doesn't even exist in the archive.
            self.close()
            if try_again:
                self.extract(filename, destination_path, False)
        elif errorcode == UnrarDll._ErrorCode.ERAR_BAD_DATA:
            self.close()

            errormessage = UnrarException.get_error_message(errorcode)
            raise UnrarException("Couldn't extract file: %s" % errormessage)

        # After the method returns, the RAR handler is still open and pointing
        # to the next archive file. This will improve extraction speed for sequential file reads.
        # After all files have been extracted, close() should be called to free the handler resources.

    def close(self):
        """ Close the archive handle """
        if self._handle:
            self._close(self._handle)
            self._handle = None

    def _open(self, path, openmode):
        """ Opens the rar file specified by <path> and returns its handle. """
        assert isinstance(path, unicode), "Path must be Unicode string"

        archivedata = UnrarDll._RAROpenArchiveDataEx(ArcNameW=path, OpenMode=openmode)

        handle = self._unrar.RAROpenArchiveEx(ctypes.byref(archivedata))
        if handle:
            if sys.platform == 'win32':
                callback_type = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint,
                    ctypes.c_long, ctypes.c_long, ctypes.c_long)
            else:
                callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint,
                    ctypes.c_long, ctypes.c_long, ctypes.c_long)

            self._callback_function = callback_type(self._password_callback)
            self._unrar.RARSetCallback(handle, self._callback_function, 0)
            return handle
        else:
            errormessage = UnrarException.get_error_message(archivedata.OpenResult)
            raise UnrarException("Couldn't open archive: %s" % errormessage)

    def _close(self, handle):
        """ Close the rar handle previously obtained by open. """
        errorcode = self._unrar.RARCloseArchive(handle)

        if errorcode != 0:
            errormessage = UnrarException.get_error_message(errorcode)
            raise UnrarException("Couldn't close archive: %s" % errormessage)

    def _password_callback(self, msg, userdata, buffer_address, buffer_size):
        """ Called by the unrar library in case of missing password. """
        if msg == 2: # UCM_NEEDPASSWORD
            # Abort extraction
            return -1
        else:
            # Continue operation
            return 1

class UnrarException(Exception):
    """ Exception class for UnrarDll. """

    _exceptions = {
        UnrarDll._ErrorCode.ERAR_END_ARCHIVE: "End of archive",
        UnrarDll._ErrorCode.ERAR_NO_MEMORY:" Not enough memory to initialize data structures",
        UnrarDll._ErrorCode.ERAR_BAD_DATA: "Bad data, CRC mismatch",
        UnrarDll._ErrorCode.ERAR_BAD_ARCHIVE: "Volume is not valid RAR archive",
        UnrarDll._ErrorCode.ERAR_UNKNOWN_FORMAT: "Unknown archive format",
        UnrarDll._ErrorCode.ERAR_EOPEN: "Volume open error",
        UnrarDll._ErrorCode.ERAR_ECREATE: "File create error",
        UnrarDll._ErrorCode.ERAR_ECLOSE: "File close error",
        UnrarDll._ErrorCode.ERAR_EREAD: "Read error",
        UnrarDll._ErrorCode.ERAR_EWRITE: "Write error",
        UnrarDll._ErrorCode.ERAR_SMALL_BUF: "Buffer too small",
        UnrarDll._ErrorCode.ERAR_UNKNOWN: "Unknown error",
        UnrarDll._ErrorCode.ERAR_MISSING_PASSWORD: "Password missing"
    }

    @staticmethod
    def get_error_message(errorcode):
        if errorcode in UnrarException._exceptions:
            return UnrarException._exceptions[errorcode]
        else:
            return "Unkown error"

# Filled on-demand by _get_unrar_dll
_unrar_dll = -1

def _get_unrar_dll():
    """ Tries to load libunrar and will return a handle of it.
    Returns None if an error occured or the library couldn't be found. """
    global _unrar_dll
    if _unrar_dll != -1:
        return _unrar_dll

    # Load unrar.dll on win32
    if sys.platform == 'win32':

        # First, search for unrar.dll in PATH
        unrar_path = ctypes.util.find_library("unrar.dll")
        if unrar_path:
            try:
                return ctypes.windll.LoadLibrary(unrar_path)
            except WindowsError:
                pass

        # The file wasn't found in PATH, try MComix' root directory
        try:
            return ctypes.windll.LoadLibrary(os.path.join(constants.BASE_PATH, "unrar.dll"))
        except WindowsError:
            pass

        # Last attempt, just use the current directory
        try:
            _unrar_dll = ctypes.windll.LoadLibrary("unrar.dll")
        except WindowsError:
            _unrar_dll = None

        return _unrar_dll

    # Load libunrar.so on UNIX
    else:
        # find_library on UNIX uses various mechanisms to determine the path
        # of a library, so one could assume the library is not installed
        # when find_library fails
        unrar_path = ctypes.util.find_library("unrar") or \
            '/usr/lib/libunrar.so'

        if unrar_path:
            try:
                _unrar_dll = ctypes.cdll.LoadLibrary(unrar_path)
                return _unrar_dll
            except OSError:
                pass

        # Last attempt, try the current directory
        try:
            _unrar_dll = ctypes.cdll.LoadLibrary(os.path.join(os.getcwd(), "libunrar.so"))
        except OSError:
            _unrar_dll = None

        return _unrar_dll

# vim: expandtab:sw=4:ts=4
