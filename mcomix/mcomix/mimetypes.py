import mimetypes

# not registered in mimetypes
additional_types=(
    ('.cb7','application/x-cb7'),
    ('.cbr','application/x-cbr'),
    ('.rar','application/x-rar'),
    ('.cbt','application/x-cbt'),
    ('.cbz','application/x-cbz'),
)

if not mimetypes.inited:
    mimetypes.init()

    for suffix,mime in additional_types:
        if suffix not in mimetypes.types_map:
            mimetypes.add_type(mime,suffix)

def guess_type(*args,**kwargs):
    return mimetypes.guess_type(*args,**kwargs)
