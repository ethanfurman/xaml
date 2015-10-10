from __future__ import print_function, unicode_literals
from antipathy import Path
from scription import *
from string import maketrans
from xaml import Xaml
from xml.etree import ElementTree as ET
import sys


Script(
        encoding=('encoding of source file [default: UTF-8]', OPTION),
        display=('send output to stdout instead of to DEST', FLAG, None),
        )


@Command(
        file=('xaml file to convert to xml', REQUIRED, 'f', Path),
        dest=('name of destination file [default: same name with .xaml -> .xml]', OPTION, 'd', Path),
        same_dir=('create DEST in same directory as FILE [default: current directory]', FLAG),
        type=Spec('specify type of document to convert to', OPTION, choices=['xml','html']),
        )
def xaml(file, dest, same_dir, type):
    "convert FILE to xml/html/css/..."
    if dest is None:
        if file.ext == '.xaml':
            dest = file.strip_ext()
        else:
            dest = file
    if not same_dir:
        dest = dest.filename
    with open(file) as source:
        xaml_doc = Xaml(source.read(), doc_type=type).document
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


@Command(
        src=Spec('xml file(s) to convert to xaml', type=Path),
        )
def from_xml(*src):
    "convert xml file to xaml"
    for s in src:
        root = ET.parse(s).getroot()
        if s.ext == '.xml':
            dst = s.strip_ext() + '.xaml'
        else:
            dst = s + '.xaml'
        print('convert %s to %s' % (s, dst))
        if display:
            write_xaml(root, sys.stdout)
        else:
            with dst.open('w') as fh:
                write_xaml(root, fh)


def write_xaml(child, fh, level=0):
    "child = xml element, fh = open file, level = indentation"
    print('   ' * level + str(child), verbose=2)
    if level == 0:
        fh.write(b'!!! xml1.0\n')
    elif level == 2:
        fh.write(b'\n')
    line = ['    ' * level]
    attrib = child.attrib.copy()
    name = attrib.pop('name', None)
    id = attrib.pop('id', None)
    string = attrib.pop('string', None)
    model = attrib.pop('model', None)
    cls = attrib.pop('class', None)
    text = (child.text or '').strip()
    tail = (child.tail or '').strip()
    if name and child.tag == 'field':
        line[0] += '@' + name
        name = None
    else:
        line[0] += '%' + child.tag
    if name:
        if bad_name(name) or ' ' in name:
            line.append('name=%r' % name)
        else:
            line.append('@' + name)
    if string:
        if bad_name(string):
            line.append('string=%r' % string)
        else:
            line.append('$' + string.replace(' ','_'))
    if model:
        line.append('model=%r' % model)
    if cls:
        if ' ' in cls:
            line.append('class=%r' % cls)
        else:
            line.append('.' + cls)
    if id:
        if bad_name(id):
            line.append('id=%r' % id)
        else:
            line.append('#' + id)
    for k in sorted(attrib.keys()):
        line.append('%s=%r' % (k, child.attrib[k]))
    line = ' '.join(line)
    if text:
        if '\n' in text or child.tag in ('p', 'div', 'html', 'body'):
            text = ' '.join(text.split())
        else:
            line += ': %s' % text
            text = None
    fh.write((line + '\n').encode('utf-8'))
    if text:
        print(('   ' * (level+1) + child.tag + '.text: ' + text).encode('utf-8'), verbose=2)
        fh.write(('    ' * (level+1) + text + '\n').encode('utf-8'))
    if tail:
        print(('   ' * level + child.tag + '.tail: ' + tail).encode('utf-8'), verbose=2)
        fh.write(('    ' * level + tail + '\n').encode('utf-8'))
    for grandchild in child:
        write_xaml(grandchild, fh, level+1)

_strip_sentinel = object()
def translator(frm=b'', to=b'', delete=b'', keep=b'', strip=_strip_sentinel):
    if len(to) == 1:
        to = to * len(frm)
    bytes_trans = maketrans(frm, to)
    if keep is not None:
        allchars = maketrans(b'', b'')
        delete = allchars.translate(allchars, keep.translate(allchars, delete)+frm)
    uni_table = {}
    for src, dst in zip(frm, to):
        uni_table[ord(src)] = ord(dst)
    for chr in delete:
        uni_table[ord(chr)] = None
    def translate(s):
        if isinstance(s, unicode):
            s = s.translate(uni_table)
            if keep is not None:
                del_table = {}
                for chr in set(s) - set(keep):
                    del_table[ord(chr)] = None
                s = s.translate(del_table)
        else:
            s = s.translate(bytes_trans, delete)
        if strip is not _strip_sentinel:
            s = s.strip(strip)
        return s
    return translate

bad_name = translator(keep=b"""!"#$%&'()*+,/;<=>?@[\\]^`{|}~\n""")

Run()
