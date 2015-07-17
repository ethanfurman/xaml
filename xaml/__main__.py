from __future__ import print_function, unicode_literals
from antipathy import Path
from scription import *
from xaml import Xaml

Script(
        encoding=('encoding of source file [default: UTF-8]', OPTION),
        display=('send output to stdout instead of to DEST', FLAG, None),
        )


@Command(
        file=('xaml file to convert to xml', REQUIRED, 'f', Path),
        dest=('name of destination file [default: same name with .xaml -> .xml]', OPTION, 'd', Path),
        same_dir=('create DEST in same directory as FILE [default: current directory]', FLAG),
        )
def xaml(file, dest, same_dir):
    "convert FILE to xml/html/css/..."
    if dest is None:
        if file.ext == '.xaml':
            dest = file.strip_ext()
        else:
            dest = file
    if not same_dir:
        dest = dest.filename
    with open(file) as source:
        xaml_doc = Xaml(source.read()).document
    if display:
        print(xaml_doc.string(), verbose=0)
    else:
        dest += '.' + xaml_doc.ml.type
        with open(dest, 'wb') as target:
            target.write(xaml_doc.bytes())


@Command(
        file=('xaml file to convert to xml', REQUIRED, 'f', Path),
        )
def tokens(file):
    "convert FILE to token format"
    with open(file) as source:
        result = Xaml(source.read(), _compile=False)
    for token in result._tokens:
        print(token, verbose=0)


@Command(file=('xaml file to convert', REQUIRED, 'f', Path),
        )
def code(file):
    "convert FILE to code used to create final output"
    with open(file) as source:
        result = Xaml(source.read(), _compile=False)
    print(result.document.code, verbose=0)

Main()
