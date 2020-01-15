# -*- coding: utf-8 -*-
''' functions to backup and upgrade config files come from mcomix 1.2.1 '''

import json
import pickle
import os
import shlex

from mcomix import log

def legacy_pickle_loader(fp):
    return pickle.Unpickler(fp,fix_imports=True,encoding='latin1')

def fileinfo_conv(fileinfo_pickle,fileinfo_json):
    try:
        with open(fileinfo_pickle,mode='rb') as f:
            loader=legacy_pickle_loader(f)
            fileinfo=loader.load()
    except Exception as e:
        log.warning('! Failed to upgrade {}, {}'.format(fileinfo_pickle,str(e)))
    else:
        with open(fileinfo_json,mode='wt',encoding='utf8') as f:
            json.dump(fileinfo,f,indent=2)
        os.rename(fileinfo_pickle,fileinfo_pickle+'.bak')

def bookmarks_conv(bookmarks_pickle,bookmarks_json):
    try:
        with open(bookmarks_pickle,mode='rb') as f:
            loader=legacy_pickle_loader(f)
            version=loader.load()
            bookmarks=[(name,path,page,numpages,packtype,date.timestamp())
                       for name,path,page,numpages,packtype,date in loader.load()]
    except Exception as e:
        log.warning('! Failed to upgrade {}, {}'.format(bookmarks_pickle,str(e)))
    else:
        with open(bookmarks_json,mode='wt',encoding='utf8') as f:
            json.dump((version,bookmarks),f,indent=2)
        os.rename(bookmarks_pickle,bookmarks_pickle+'.bak')

def openwith_conv(prefs):

    class OldOpenWithException(Exception): pass

    def _expand_variable_old(identifier, window, context_type):
        # keep this functions only for reference
        ''' Replaces variables with their respective file
        or archive path. '''

        DEBUGGING_CONTEXT, NO_FILE_CONTEXT, IMAGE_FILE_CONTEXT, ARCHIVE_CONTEXT = -1, 0, 1, 2

        if context_type == DEBUGGING_CONTEXT:
            return '%' + identifier

        if not (context_type & IMAGE_FILE_CONTEXT) and identifier in ('f', 'd', 'b', 's', 'F', 'D', 'B', 'S'):
            raise OldOpenWithException(
                _('File-related variables can only be used for files.'))

        if not (context_type & ARCHIVE_CONTEXT) and identifier in ('a', 'c', 'A', 'C'):
            raise OldOpenWithException(
                _('Archive-related variables can only be used for archives.'))

        if identifier == '/':
            return os.path.sep
        elif identifier == 'a':
            return window.filehandler.get_base_filename()
        elif identifier == 'd':
            return os.path.basename(os.path.dirname(window.imagehandler.get_path_to_page()))
        elif identifier == 'f':
            return window.imagehandler.get_page_filename()
        elif identifier == 'c':
            return os.path.basename(os.path.dirname(window.filehandler.get_path_to_base()))
        elif identifier == 'b':
            if (context_type & ARCHIVE_CONTEXT):
                return window.filehandler.get_base_filename() # same as %a
            else:
                return os.path.basename(os.path.dirname(window.imagehandler.get_path_to_page())) # same as %d
        elif identifier == 's':
            if (context_type & ARCHIVE_CONTEXT):
                return os.path.basename(os.path.dirname(window.filehandler.get_path_to_base())) # same as %c
            else:
                return os.path.basename(os.path.dirname(os.path.dirname(window.imagehandler.get_path_to_page())))
        elif identifier == 'A':
            return window.filehandler.get_path_to_base()
        elif identifier == 'D':
            return os.path.normpath(os.path.dirname(window.imagehandler.get_path_to_page()))
        elif identifier == 'F':
            return os.path.normpath(window.imagehandler.get_path_to_page())
        elif identifier == 'C':
            return os.path.dirname(window.filehandler.get_path_to_base())
        elif identifier == 'B':
            if (context_type & ARCHIVE_CONTEXT):
                return window.filehandler.get_path_to_base() # same as %A
            else:
                return os.path.normpath(os.path.dirname(window.imagehandler.get_path_to_page())) # same as %D
        elif identifier == 'S':
            if (context_type & ARCHIVE_CONTEXT):
                return os.path.dirname(window.filehandler.get_path_to_base()) # same as %C
            else:
                return os.path.dirname(os.path.dirname(window.imagehandler.get_path_to_page()))
        else:
            raise OldOpenWithException(
                'Invalid escape sequence: %{}'.format(identifier))

    def _expand_variable(identifier):
        identifier_map = {
            '/': os.path.sep,
            'F': '{image}',
            'f': '{imagebase}',
            'D': '{imagedir}',
            'd': '{imagedirbase}',
            'A': '{archive}',
            'a': '{archivebase}',
            'C': '{archivedir}',
            'c': '{archivedirbase}',
            'B': '{container}',
            'b': '{containerbase}',
            'S': '{containerdir}',
            's': '{containerdirbase}',
        }
        try:
            return identifier_map[identifier]
        except:
            raise OldOpenWithException(
                'Invalid escape sequence: %{}'.format(identifier))

    def _old_cmd_to_args(line):
        ''' Parse a command line string into a list containing
        the parts to pass to Popen. The following two functions have
        been contributed by Ark <aaku@users.sf.net>. '''
        result = []
        buf = ''
        quote = False
        escape = False
        inarg = False
        for c in line:
            if escape:
                if c == '%' or c == '"':
                    buf += c
                else:
                    buf += _expand_variable(c)
                escape = False
            elif c == ' ' or c == '\t':
                if quote:
                    buf += c
                elif inarg:
                    result.append(buf)
                    buf = ''
                    inarg = False
            else:
                if c == '"':
                    quote = not quote
                elif c == '%':
                    escape = True
                else:
                    buf += c
                inarg = True

        if escape:
            raise OldOpenWithException(
                _('Incomplete escape sequence. '
                  'For a literal "%", use "%%".'))
        if quote:
            raise OldOpenWithException(
                _('Incomplete quote sequence. '
                  'For a literal "\'", use "%\'".'))

        if inarg:
            result.append(buf)
        return result

    prefs['external commands']=[]
    # convert old style command if exists
    for label, command, *params in prefs['openwith commands']:
        if not params:
            params.extend(('', False))
        cwd, disabled_for_archives = params
        for c in ('{','}'):
            command = command.replace(c, c*2)
        try:
            newcmd_args = _old_cmd_to_args(command.strip())
        except Exception as e:
            log.warning('! '+str(e))
            continue
        new_command = ' '.join(map(shlex.quote, newcmd_args))
        prefs['external commands'].append(
            (label, new_command, cwd.strip(), bool(disabled_for_archives))
        )
    prefs['openwith commands'].clear()
