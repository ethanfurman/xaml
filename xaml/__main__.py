from antipathy import Path
from scription import *
from xaml import Xaml

Script(
        encoding=('encoding of source file [default: UTF-8]', OPTION),
        )

@Command(
        file=('xaml file to convert to xml', REQUIRED, 'f', Path),
        dest=('name of destination file [default: same name with .xaml -> .xml]', OPTION, 'd', Path),
        display=('send output to stdout instead of to DEST', FLAG, None),
        same_dir=('create DEST in same directory as FILE [default: current directory]', FLAG),
        )
def xaml(file, dest, display, same_dir):
    if dest is None:
        if file.ext == '.xaml':
            dest = file.strip_ext() + '.xml'
        else:
            dest = file + '.xml'
    if not same_dir:
        dest = dest.filename
    with open(file) as source:
        result = Xaml(source.read()).parse()
    if display:
        print(result)
    else:
        with open(dest, 'wb') as target:
            target.write(result)


Main()
