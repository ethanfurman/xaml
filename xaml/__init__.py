"""xaml -- xml abstract markup language

https://bitbucket.org/stoneleaf/xaml

Copyright 2015 Ethan Furman -- All rights reserved.
"""
from __future__ import unicode_literals
from enum import Enum
import re
import sys
import unicodedata

__all__ = ['Xaml', ]
__metaclass__ = type

version = 0, 3, 3

module = globals()

try:
    unicode
except NameError:
    unicode = str
    unichr = chr

# only change default_encoding if you cannot specify the proper encoding with a meta tag
default_encoding = 'utf-8'

# helprs {{{1
class AutoEnum(Enum):
    """
    Automatically numbers enum members starting from 1.
    Includes support for a custom docstring per member.
    """

    __last_number__ = 0

    def __new__(cls, *args):
        """Ignores arguments (will be handled in __init__."""
        value = cls.__last_number__ + 1
        cls.__last_number__ = value
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, *args):
        """Can handle 0 or 1 argument; more requires a custom __init__.
        0  = auto-number w/o docstring
        1  = auto-number w/ docstring
        2+ = needs custom __init__
        """
        if len(args) == 1 and isinstance(args[0], (str, unicode)):
            self.__doc__ = args[0]
        elif args:
            raise TypeError('%s not dealt with -- need custom __init__' % (args,))

    @classmethod
    def export_to(cls, namespace):
        for name, member in cls.__members__.items():
            if name == member.name:
                namespace[name] = member

class State(AutoEnum):
    CONTENT = 'collecting content'
    DATA    = 'collecting element data'
    DENTING = 'calculating in/de-dents'
    ELEMENT = 'collecting element pieces'
    FILTER  = 'collecting filter text'
    NORMAL  = 'looking for next xaml header'
    PARENS  = 'skipping oel until closing paren'
    QUOTES  = 'oel converted to space, continuing lines must have greater indentation than first line'
s = State

class TokenType(AutoEnum):
    COMMENT     = 'a comment'
    CONTENT     = 'general content'
    CODE_ATTR   = 'an element attribute as python code'
    CODE_DATA   = "an element's data as code"
    DEDENT      = 'less space than before'
    ELEMENT     = 'name of current xaml element'
    FILTER      = 'filter lines'
    INDENT      = 'more space than before'
    META        = 'meta information'
    BLANK_LINE  = 'a whole new line'
    STR_ATTR    = 'an element attribute as a string'
    STR_DATA    = "an element's data as a string"
    PYTHON      = 'python code'
    SYMBOL      = 'something special'
    TEXT        = 'text to go with something special'
tt = TokenType


def _leading(line):
    """
    returns number of spaces before text
    """
    return len(line) - len(lstrip(line, ' '))

invalid_xml_chars = []
for r in (
    range(0, 9),
    range(0x0b, 0x0d),
    range(0x0e, 0x20),
    range(0xd800, 0xdfff),
    range(0xfffe, 0x10000),
    ):
    for n in r:
        invalid_xml_chars.append(unichr(n))
invalid_xml_chars = tuple(invalid_xml_chars)


# pushable iter for text stream {{{1
class PPLCStream:
    """
    Peekable, Pushable, Line & Character Stream
    """

    current_line = None

    def __init__(self, text):
        if not isinstance(text, unicode):
            if text.startswith(b'!!! coding:'):
                first_line = text.find(b'\n')
                if first_line == -1:
                    encoding = text[11:].strip()
                else:
                    encoding = text[11:first_line].strip()
                encoding = encoding.decode('ascii')
                if encoding:
                    try:
                        text = text.decode(encoding).rstrip().split('\n')[1:]
                    except LookupError:
                        exc = sys.exc_info()[1]
                        raise SystemExit(exc)
                else:
                    raise SystemExit("no encoding specified in '!!! coding: ...'")
            else:
                text = text.decode('ascii').rstrip().split('\n')
        else:
            text = text.rstrip().split('\n')
        for i, line in enumerate(text):
            for ch in invalid_xml_chars:
                if ch in line:
                    raise InvalidXmlCharacter(i, 'Character %r not allowed in xaml documents' % ch)
        self.data = text
        self.data.reverse()
        self.chars = []
        self.lines = []
        self.line = 0

    def get_char(self):
        if not self.chars:
            line = self.get_line()
            if line is None:
                return None
            self.chars = list(line)
        return self.chars.pop(0)

    def get_line(self):
        if self.chars:
            line = ''.join(self.chars).rstrip('\n')
            self.chars = []
        elif self.lines:
            line = self.lines.pop()
            self.line += 1
        elif self.data:
            line = self.data.pop()
            self.line += 1
        else:
            self.current_line = None
            return None
        line += '\n'
        self.current_line = line
        return line

    def peek_char(self):
        ch = self.get_char()
        self.push_char(ch)
        return ch

    def peek_line(self):
        line = self.get_line()
        self.push_line(line)
        return line

    def push_char(self, ch):
        if ch is None:
            return
        if ch == '\n':
            if self.chars:
                # convert existing chars to line, dropping newline char
                char_line = ''.join(self.chars).rstrip('\n')
                self.chars = []
                if char_line:
                    self.lines.append(char_line.rstrip('\n'))
                    self.lines -= 1
            self.chars = [ch]
        elif not self.chars:
            # nothing already in chars, and newline not being pushed,
            # so get an existing line to add to
            line = self.get_line()
            if line is None:
                line = '\n'
            self.chars = list(line)
            self.chars.insert(0, ch)
        else:
            self.chars.insert(0, ch)

    def push_line(self, line):
        if line is None:
            return
        if self.chars:
            char_line = ''.join(self.chars).rstrip('\n')
            self.chars = []
            if char_line:
                self.lines.append(char_line.rstrip('\n'))
                self.line -= 1
        self.line -= 1
        line = line.rstrip('\n')
        self.lines.append(line)
        self.current_line = line


# Token and Tokenizer {{{1
class Token:

    def __init__(self, ttype, payload=None, make_safe=True):
        self.type = ttype
        if payload is not None and isinstance(payload, unicode):
            payload = (payload, )
        self.payload = payload
        self.make_safe = make_safe

    def __eq__(self, other):
        if not isinstance(other, Token):
            return NotImplemented
        for attr in ('type', 'payload', 'make_safe'):
            if getattr(self, attr) != getattr(other, attr):
                break
        else:
            return True
        return False

    def __ne__(self, other):
        if not isinstance(other, Token):
            return NotImplemented
        return not self.__eq__(other)

    def __repr__(self):
        attrs = ['%s' % self.type]
        for attr in ('payload', 'make_safe'):
            val = getattr(self, attr)
            if val is not None:
                attrs.append('%s=%r' % (attr, val))
        return 'Token(%s)' % (', '.join(attrs))


class Tokenizer:

    defaults = {
            '%' : 'field',
            '@' : 'name',
            '.' : 'class',
            '#' : 'id',
            '$' : 'string',
            }

    def __init__(self, text):
        self.data = PPLCStream(text)
        self.state = [s.NORMAL]
        self.indents = [0]
        self.open_parens = 0
        self.last_token = None

    def __next__(self):
        res = self.get_token()
        if res is None:
            raise StopIteration
        return res
    next = __next__

    def __iter__(self):
        return self

    def _consume_ws(self, line=None, include=''):
        ws = ' ' + include
        if line is None:
            while self.data.peek_char() in ws:
                self.data.get_char()
        else:
            if line:
                chars = list(reversed(list(line)))
                while chars[-1] in ws:
                    chars.pop()
                line = ''.join(reversed(chars))
            return line

    def _get_attribute(self, default=False):
        '''
        returns attribute name and value
        '''
        ws = ''
        if self.open_parens:
            ws = '\n'
        self._consume_ws(include=ws)
        # check if the element has ended
        ch = self.data.peek_char()
        if self.open_parens:
            if ch in ')':
                self.data.get_char()
                self.open_parens -= 1
                self._consume_ws()
                if self.data.peek_char() not in ('\n', None):
                    raise ParseError(self.data.line, 'nothing allowed on same line after ")"')
                return self.get_token()
        elif ch in '/:\n':
            if self.open_parens:
                raise ParseError(self.data.line, 'unclosed parens')
            self.data.get_char()
            self.state.pop()
            if ch == ':':
                if not self.data.peek_line().strip():
                    raise ParseError(self.data.line, 'nothing after :')
                self.state.append(s.DATA)
            elif ch == '/':
                self.state.append(s.CONTENT)
            return self.get_token()
        # collect the name
        name, disallow_quotes = self._get_name()
        # _get_name left ch at the '=', or the next non-ws character
        ch = self.data.peek_char()
        if ch == '=':
            self.data.get_char()
            attr_type, value = self._get_value(disallow_quotes)
            if name in ('string', ):
                value = value.replace('_', ' ')
        else:
            attr_type = tt.STR_ATTR
            value = name
        return Token(attr_type, (name, value), make_safe=True)

    def _get_comment(self):
        line = self.data.get_line().rstrip()[2:]
        if line[0] == ' ':
            line = line[1:]
        # line = self._consume_ws(line)
        return Token(tt.COMMENT, line)

    def _get_content(self):
        line = self.data.get_line().rstrip()
        return Token(tt.CONTENT, line, make_safe=True)

    def _get_data(self):
        line = self.data.get_line().strip()
        make_safe = True
        data_type = tt.STR_DATA
        if line[:2] == '!=':
            make_safe = False
            data_type = tt.CODE_DATA
            line = line[2:]
        elif line[0:1] == '=':
            data_type = tt.CODE_DATA
            line = line[1:]
        elif line[:2] == '&=':
            data_type = tt.CODE_DATA
            line = line[2:]
        line = self._consume_ws(line)
        self.state.pop()
        return Token(data_type, line, make_safe)

    def _get_denting(self):
        last_indent = self.indents[-1]
        line = self.data.get_line()
        content = line.lstrip()
        current_indent = len(line) - len(content)
        if current_indent > last_indent:
            # indent
            self.data.push_line(line)
            self.indents.append(current_indent)
            self.state.pop()
            return Token(tt.INDENT)
        else:
            # dedent
            self.indents.pop()
            target_indent = self.indents[-1]
            self.data.push_line(line)
            if current_indent == target_indent:
                self.state.pop()
                return Token(tt.DEDENT)
            else:
                self.state.pop()
                # self.data.push_line(line[last_indent-target_indent:])
                return Token(tt.DEDENT)

    def _get_element(self, default=False):
        '''
        returns either the default element name, or the specified element name
        '''
        if default:
            return Token(tt.ELEMENT, self.defaults['%'])
        name, _ = self._get_name()
        return Token(tt.ELEMENT, name)
    
    def _get_filter(self):
        name = self.data.get_line().strip()
        line = self.data.get_line()
        leading = len(line) - len(line.lstrip(' '))
        lines = [line]
        while 'more lines in filter':
            line = self.data.get_line()
            ws = len(line) - len(line.lstrip(' '))
            if ws < leading:
                self.data.push_line(line)
                break
            lines.append(line)
        self.state.pop()
        return Token(tt.FILTER, (name, ''.join(lines)))

    def _get_meta(self):
        self.data.push_line(self.data.get_line()[3:])
        name, _ = self._get_name()
        if name in ('xml', 'xml1.0'):
            name = 'xml', '1.0'
        token = Token(tt.META, name)
        self.state.pop()
        self.state.append(s.ELEMENT)
        return token

    def _get_name(self, extra_chars=(), extra_types=(), extra_terminators=()):
        """
        gets the next tag or attribute name
        """
        self._consume_ws()
        ch = self.data.get_char()
        # check for line continuation
        if ch == '(':
            self.open_parens += 1
            self._consume_ws(include='\n')
            ch = self.data.get_char()
        # check for shortcuts
        name = self.defaults.get(ch, [])
        default = False
        if name:
            # set up for getting value
            self.data.push_char('=')
            default = True
        else:
            while 'collecting characters':
                if ch in '''!"#$%&'()*+,/;<=>?@[\\]^`{|}~ \n''':
                    break
                name.append(ch)
                ch = self.data.get_char()
            name = ''.join(name)
            if not name:
                raise ParseError(self.data.line, 'null name not allowed:\n\t%s' % self.data.current_line)
            if ch in '(':
                self.open_parens += 1
            elif ch in ')':
                self.open_parens -= 1
                if self.open_parens < 0:
                    raise ParseError(self.data.line, 'mismatched parenthesis')
            elif ch == ' ':
                self._consume_ws()
            else:
                self.data.push_char(ch)
        # verify first character is legal
        ch = name[0]
        if ch in'-.' or unicodedata.category(ch)[0] == 'N':
            raise ParseError(self.data.line, 'tag name cannot start with . - or digit: %r' % name)
        return name, default

    def _get_parens(self, line):
        pass

    def _get_python(self, line):
        return Token(tt.PYTHON, line.rstrip())
    
    def _get_quoted(self, line, quote, ptr):
        result = [quote]
        ptr += 1
        while "haven't found end-quote":
            ch = 'a'
            line.find(quote, ptr) == 'a'
        pass
    
    def _get_value(self, no_quotes=False):
        self._consume_ws()
        value = []
        ch = self.data.get_char()
        quote = None
        if ch in ('"', "'", '`'):
            if no_quotes and ch != '`':
                raise ParseError(self.date.line, 'out-of-place quote')
            quote = ch
            ch = self.data.get_char()
        while 'collecting value':
            if ch is None:
                if quote:
                    raise ParseError(self.date.line, 'unclosed quote while collecting value for %r: %r' % (''.join(value), ch))
                break
            if ch == quote:
                # skip past quote and finish
                ch = self.data.get_char()
                break
            elif quote and ch != '\\':
                if ch == '\n':
                    if quote == '`':
                        raise ParseError(self.date.line, 'embedded newlines illegal in attribute level python code')
                    ch = ' '
                value.append(ch)
            elif ch in ('"', "'", '`'):
                raise ParseError(self.data.line, 'embedded quote in:\n\t%s' % self.data.current_line)
            elif ch == '\\':
                ch = self.data.get_char()
                if ch == '\n':
                    raise ParseError(self.date.line, 'newlines cannot be escaped')
                value.append(ch)
            elif ch in ' )(/:\n':
                break
            else:
                value.append(ch)
            ch = self.data.get_char()
        value = ''.join(value)
        if ch in ')':
            self.open_parens -= 1
            if self.open_parens < 0:
                raise ParseError(self.date.line, 'unbalanced parentheses')
        elif ch in '(':
            self.open_parens += 1
            self._consume_ws(include='\n')
        elif ch not in (' ', '\n', ':', '/', None):
            raise ParseError(self.date.line, 'invalid character after value %r' % ''.join(value))
        else:
            self.data.push_char(ch)
            self._consume_ws()
        if quote == '`':
            token_type = tt.CODE_ATTR
        elif quote in ('"', "'"):
            token_type = tt.STR_ATTR
        elif no_quotes:
            token_type = tt.STR_ATTR
        else:
            token_type = tt.CODE_ATTR
        return token_type, value

    def _wind_down(self):
        try:
            self.indents.pop()
        except IndexError:
            return None
        return Token(tt.DEDENT)

    def get_token(self):
        state = self.state[-1]
        if state in (s.NORMAL, s.CONTENT):
            # looking for next whatever
            while 'nothing found yet...':
                line = self.data.peek_line()
                if line is None:
                    return self._wind_down()
                if not line.strip():
                    self.data.get_line()
                    self.last_token = Token(tt.BLANK_LINE)
                    return self.last_token
                # found something, check if indentation has changed
                last_indent = self.indents[-1]
                if state is s.CONTENT and line[:last_indent].strip() == '':
                    line = self.data.get_line()
                    self.data.push_line(line[last_indent:])
                    self.last_token = self._get_content()
                    return self.last_token
                elif state is s.CONTENT:
                    self.state.pop()
                    state = self.state[-1]
                if not (line[:last_indent].lstrip() == '' and line[last_indent] != ' '):
                    self.state.append(s.DENTING)
                    self.last_token =  self._get_denting()
                    return self.last_token
                else:
                    # discard white space
                    line = self.data.get_line().lstrip()
                    self.data.push_line(line)
                    ch = line[0]
                if ch == '%':
                    self.state.append(s.ELEMENT)
                    self.data.get_char()
                    self.last_token = self._get_element()
                    return self.last_token
                elif ch in '@#.$':
                    self.state.append(s.ELEMENT)
                    self.last_token = self._get_element(default=True)
                    return self.last_token
                elif line[:2] == '//':
                    self.last_token = self._get_comment()
                    return self.last_token
                elif line[:3] == '!!!':
                    self.state.append(tt.META)
                    self.last_token = self._get_meta()
                    return self.last_token
                elif ch == ':':
                    self.state.append(s.FILTER)
                    self.data.get_char()
                    self.last_token = self._get_filter()
                    return self.last_token
                elif ch == '-':
                    self.data.get_char()
                    self.last_token = self._get_python(self.data.get_line())
                    return self.last_token
                else:
                    #must be random content
                    if self.last_token.type is tt.INDENT:
                        self.state.append(s.CONTENT)
                    self.last_token = self._get_content()
                    return self.last_token
        elif state == s.ELEMENT:
            self.last_token = self._get_attribute()
            return self.last_token
        elif state == s.DATA:
            self.last_token = self._get_data()
            return self.last_token
        else:
            raise ParseError(self.date.line, 'unknown state: %s' % state)

class ML:

    def __init__(self, text):
        text = text.strip()[2:-2]
        # if any values ever have spaces, will need to change this
        pieces = text.split()
        self.type = pieces[0]
        self.encoding = default_encoding
        self.key = None
        self.attrs = []
        found_enc = False
        for nv in pieces[1:]:
            name, value = nv.split('=', 1)
            if name == 'version':
                self.key = self.type + value.strip('"')
            if name == 'encoding':
                found_enc = True
                enc_value =  value.lower().replace('-', '').strip('"')
                if enc_value != 'utf8':
                    raise ParseError(self.date.line, 'only utf-8 is supported (not %r)' % value)
                self.encoding = enc_value
            self.attrs.append((name, value))
        if not found_enc:
            self.attrs.append(('encoding', '"%s"' % default_encoding))
        
    def __str__(self):
        res = []
        for name, value in self.attrs:
            if name == 'encoding':
                continue
            res.append('%s=%s' % (name, value))
        return '<?%s %s?>\n' % (self.type, ' '.join(res))

    def bytes(self):
        res = []
        for nv in self.attrs:
            res.append('%s=%s' % nv)
        return ('<?%s %s?>\n' % (self.type, ' '.join(res))).encode(self.encoding)


# xaml itself {{{1
class Xaml(object):

    def __init__(self, text, _parse=True, _compile=True):
        # indents tracks valid indentation levels
        self._tokens = list(Tokenizer(text))
        self._depth = [Token(None)]
        self._indents = Indent(level=1)
        self._coder = minimal
        self.ml = None
        self._encoding = default_encoding
        if _parse:
            self._document = self._parse(_compile=_compile)
        else:
            self._document = None

    @property
    def document(self):
        return self._document

    def _append_newline(self):
        if self._depth[-1].type not in (tt.INDENT, tt.BLANK_LINE, None):
            self._depth.append(Token(tt.BLANK_LINE))

    def _check_for_newline(self, token):
        if token.type is not tt.BLANK_LINE:
            return token, False
        else:
            return self._depth[-2], self._depth.pop()

    def _parse(self, _parse=True, _compile=True):
        encoding_specified = False
        output = []
        attrs = {}
        for token in self._tokens:
            # print 'depth:', ','.join(t.type.name for t in self._depth[1:])
            last_token = self._depth and self._depth[-1] or Token(None)
            if last_token.type is tt.META:
                if token.type is tt.STR_ATTR:
                    name, value = token.payload
                    if last_token.payload[0] == 'xml':
                        if not encoding_specified and name == 'encoding':
                            encoding_specified = True
                    output[-1] += ' %s="%s"' % (name, value)
                    continue
                elif token.type not in (tt.CODE_ATTR, tt.STR_DATA, tt.CODE_DATA):
                    output[-1] += '?>\n'
                    self.ml= ML(output.pop())
                    self._coder = ml_types.get(self.ml.key)
                    if self._coder is None:
                        raise ParseError(self.date.line, 'markup language %r not supported' % self.ml.type)
                    self._depth.pop()
                    if token.type is tt.DEDENT:
                        break
                else:
                    raise SystemExit('Token %s not allowed in/after META token' % token)
            elif last_token.type is tt.COMMENT:
                if token.type is not tt.COMMENT:
                    output.append(self._indents.blanks + '        )\n')
                    self._depth.pop()
                    last_token = self._depth[-1]
            if token.type in (tt.CODE_ATTR, tt.STR_ATTR):
                assert last_token.type is tt.ELEMENT, 'the tokenizer is busted (ATTR and last is %r [current: %r])' % (last_token, token)
                name, value = token.payload
                if token.type is tt.CODE_ATTR:
                    attrs[name] = value
                if token.type is tt.STR_ATTR and token.make_safe:
                    value = self._coder(value)
                    attrs[name] = repr(value)
            # COMMENT
            elif token.type is tt.COMMENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                if last_token.type is tt.ELEMENT:
                    output[-1] += ', attrs={%s})\n' % ', '.join(['%r:%s' % (k, v) for k, v in attrs.items()])
                    attrs = {}
                    self._depth.pop()
                    if pending_newline:
                        self._append_newline()
                if pending_newline:
                    output.append(self._indents.blanks + 'Blank()\n')
                if self._depth[-1].type is not tt.COMMENT:
                    self._depth.append(token)
                    output.append(self._indents.blanks + 'Comment(\n')
                output.append(self._indents.blanks + '        %r,\n' % token.payload)
            # CONTENT
            elif token.type is tt.CONTENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                if last_token.type is tt.ELEMENT:
                    # close previous element
                    output[-1] += ', attrs={%s})\n' % ', '.join(['%r:%s' % (k, v) for k, v in attrs.items()])
                    attrs = {}
                    self._depth.pop()
                if pending_newline:
                    output.append(self._indents.blanks + 'Blank()\n')
                    self._append_newline()
                output.append(self._indents.blanks + 'Content(%r)\n' % token.payload)
            # DATA
            elif token.type in (tt.CODE_DATA, tt.STR_DATA):
                string = ', attrs={%s})' % ', '.join(['%r:%s' % (k, v) for k, v in attrs.items()])
                attrs = {}
                value ,= token.payload
                if token.type is tt.CODE_DATA:
                    pass
                if token.type is tt.STR_DATA:
                    if token.make_safe:
                        value = self._coder(value)
                    value = repr(value)
                token = self._depth.pop()
                string += '(%s)\n' % value
                output[-1] += string
            # DEDENT
            elif token.type is tt.DEDENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                # need to close the immediately preceeding tag, and the
                # tags dedented to
                self._indents.dec()
                if last_token.type is tt.ELEMENT:
                    output[-1] += ', attrs={%s})\n' % ', '.join(['%r:%s' % (k, v) for k, v in attrs.items()])
                    attrs = {}
                    self._depth.pop()
                should_be_indent = self._depth.pop()
                assert should_be_indent.type in (tt.INDENT, None), 'something broke: %s\n%s' % (should_be_indent, ''.join(output))
                try:
                    last_token = self._depth[-1]
                except IndexError:
                    # all done!
                    break
                if last_token.type is tt.BLANK_LINE:
                    output.append('\n')
                    self._depth.pop()
                    last_token = self._depth[-1]
                    self._indents.dec()
                if last_token.type is tt.ELEMENT:
                    closing_token = self._depth.pop()
                if pending_newline:
                    self._depth.append(pending_newline)
            # ELEMENT
            elif token.type is tt.ELEMENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                if last_token.type is tt.ELEMENT:
                    # close previous element
                    output[-1] += ', attrs={%s})\n' % ', '.join(['%r:%s' % (k, v) for k, v in attrs.items()])
                    attrs = {}
                    self._depth.pop()
                if pending_newline:
                    output.append(self._indents.blanks + 'Blank()\n')
                    self._append_newline()
                output.append(self._indents.blanks)
                output.append('Element(%r' % token.payload)
                self._depth.append(token)
            # FILTER
            elif token.type is tt.FILTER:
                name, lines = token.payload
                if name == 'python':
                    blank = self._indents.blanks
                    output.append(blank + 'if 1:\n')
                    for line in lines.split('\n'):
                        output.append(blank + line + '\n')
                else:
                    raise ParseError(self.date.line, 'unknown filter: %r' % name)
            # INDENT
            elif token.type is tt.INDENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                with_ele = False
                if last_token.type is tt.ELEMENT:
                    output[-1] = 'with %s, attrs={%s}):\n' % (output[-1], ', '.join(['%r:%s' % (k, v) for k, v in attrs.items()]))
                    attrs = {}
                    with_ele = True
                self._indents.inc()
                if pending_newline:
                    if with_ele:
                        output.append(self._indents.blanks + 'with Blank(mirror=True):\n')
                        self._indents.inc()
                    else:
                        output.append(self._indents.blanks + 'Blank()\n')
                    self._append_newline()
                self._depth.append(token)
            # META
            elif token.type is tt.META:
                if len(self._depth) != 1 or self._depth[0].type != None:
                    raise ParseError(self.date.line, 'meta tags (such as %r) cannot be nested' % token.payload)
                name, value = token.payload
                if name == 'xml':
                    output.append('<?xml version="%s"' % value)
                else:
                    raise SystemExit('unknown META: %r' % ((name, value)))
                self._depth.append(token)
            # PYTHON
            elif token.type is tt.PYTHON:
                last_token, pending_newline = self._check_for_newline(last_token)
                if last_token.type is tt.ELEMENT:
                    # close previous element
                    output[-1] += ', attrs={%s})\n' % ', '.join(['%r:%s' % (k, v) for k, v in attrs.items()])
                    attrs = {}
                    self._depth.pop()
                if pending_newline:
                    output.append(self._indents.blanks + 'Blank()\n')
                    self._append_newline()
                output.append(self._indents.blanks + '%s\n' % token.payload)
            # BLANK_LINE
            elif token.type is tt.BLANK_LINE:
                if last_token.type is tt.BLANK_LINE:
                    continue
                else:
                    self._depth.append(token)
            # problem
            else:
                raise ParseError(self.date.line, 'unknown token: %r' % token)
        global_code = [
                """output = []\n""",
                """\n""",
                """class Args:\n""",
                """    def __init__(self, kwds):\n""",
                """        for k, v in kwds.items():\n""",
                """            setattr(self, k, v)\n""",
                """\n""",
                """class Blank:\n""",
                """    def __init__(self, mirror=False):\n""",
                """        self.mirror = mirror\n""",
                """        output.append('')\n""",
                """    def __enter__(self):\n""",
                """        pass\n""",
                """    def __exit__(self, *args):\n""",
                """        if self.mirror:\n""",
                """            output.append('')\n""",
                """\n""",
                """def Comment(*content):\n""",
                """    output.append('%s<!--' % indent.blanks)\n""",
                """    for line in content:\n""",
                """        output.append('%s |  %s' % (indent.blanks, line))\n""",
                """    output.append('%s-->' % indent.blanks)\n""",
                """\n""",
                """def Content(content):\n""",
                """    output.append('%s%s' % (indent.blanks, content))\n""",
                """\n""",
                """class Element:\n""",
                """    def __init__(self, tag, attrs={}):\n""",
                """        self.tag = tag\n""",
                """        attrs = ' '.join(['%s="%s"' % (k, v) for k, v in attrs.items()])\n"""
                """        if attrs:\n""",
                """            attrs = ' ' + attrs\n""",
                """        output.append('%s<%s%s/>' % (indent.blanks, tag, attrs))\n""",
                """    def __call__(self, content):\n""",
                """        output[-1] = output[-1][:-2] + '>%s</%s>' % (content, self.tag)\n""",
                """    def __enter__(self):\n""",
                """        if output and output[-1] == '':\n""",
                """            target = -2\n""",
                """        else:\n""",
                """            target = -1\n""",
                """        indent.inc()\n""",
                """        output[target] = output[target][:-2] + '>'\n""",
                """    def __exit__(self, *args):\n""",
                """        indent.dec()\n""",
                """        output.append('%s</%s>' % (indent.blanks, self.tag))\n""",
                """\n""",
                """indent = Indent()\n""",
                """\n""",
                ]
        pre_code = [
                """def generate(**kwds):\n""",
                """    args = Args(kwds)\n""",
                """\n""",
                ]
        post_code = [
                """\n""",
                # """    print '\\n\\n'\n"""
                # """    print '\\n'.join(output)\n"""
                """    return '\\n'.join(output)""",
                ]
        # print ''.join(pre_code+output+post_code)
        code = ''.join(pre_code+output+post_code)
        glbls = globals().copy()
        exec(''.join(global_code), glbls)
        if _compile:
            exec(code, glbls)
            return XamlDoc(self.ml, code, glbls['generate'])
        else:
            return XamlDoc(self.ml, code, None)


class XamlDoc:

    def __init__(self, ml, code, func):
        self.ml = ml
        self._code = code
        self._func = func
        if self.ml is not None:
            self.encoding = ml.encoding
        else:
            self.encoding = default_encoding

    def __repr__(self):
        return '<%s document>' % (self.ml and self.ml.type or 'generic ml')

    @property
    def code(self):
        return self._code

    def string(self, **kwds):
        text = self._func(**kwds)
        return str(self.ml or '') + text

    def bytes(self, **kwds):
        text = self._func(**kwds)
        return (self.ml and self.ml.bytes() or b'') + text.encode(self.encoding)


class Indent:

    def __init__(self, blank='    ', level=0):
        self.blank = blank
        self.indent = level

    def inc(self):
        self.indent += 1

    def dec(self):
        self.indent -= 1

    @property
    def blanks(self):
        return self.blank * self.indent


class ParseError(Exception):
    '''
    Used for xaml parse errors
    '''

    line_no = None

    def __init__(self, line_no, message=None):
        if message is None:
            Exception.__init__(self, line_no)
        else:
            self.line_no = line_no
            Exception.__init__(self, 'line %s: %s' % (line_no, message))


class InvalidXmlCharacter(ParseError):
    '''
    Used for invalid code points
    '''


def minimal(text):
    cp = {
        '<' : '&lt;',
        '>' : '&gt;',
        '&' : '&amp;',
        '"' : '&#x22;',
        }
    result = []
    for ch in text:
        ch = cp.get(ch, ch)
        result.append(ch)
    return ''.join(result)

xmlify = minimal

ml_types = {
    'xml1.0' : xmlify,
    }
