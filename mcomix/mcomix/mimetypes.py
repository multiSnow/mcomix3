import mimetypes

from mcomix import constants

if not mimetypes.inited:
    mimetypes.init()
    for suffix,mime in constants.ARCHIVE_FORMATS:
        if suffix not in mimetypes.types_map:
            mimetypes.add_type(mime,suffix)

def guess_type(*args,**kwargs):
    return mimetypes.guess_type(*args,**kwargs)
