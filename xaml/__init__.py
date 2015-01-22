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

version = 0, 1, 8

module = globals()

try:
    unicode
except NameError:
    unicode = str


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
    SYMBOL      = 'something special'
    TEXT        = 'text to go with something special'
tt = TokenType


def _leading(line):
    """
    returns number of spaces before text
    """
    return len(line) - len(lstrip(line, ' '))


# pushable iter for text stream {{{1
class PPLCStream:
    """
    Peekable, Pushable, Line & Character Stream
    """

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
            return None
        line += '\n'
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


# Token and Tokenizer {{{1
class Token:

    def __init__(self, ttype, payload=None, xml_safe=None):
        self.type = ttype
        if payload is not None and isinstance(payload, unicode):
            payload = (payload, )
        self.payload = payload
        self.xml_safe = xml_safe

    def __eq__(self, other):
        if not isinstance(other, Token):
            return NotImplemented
        for attr in ('type', 'payload', 'xml_safe'):
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
        for attr in ('payload', 'xml_safe'):
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
                    raise ParseError('line %d: nothing allowed on same line after ")"' % self.data.line)
                return self.get_token()
        elif ch in '/:\n':
            if self.open_parens:
                raise ParseError('line %d: unclosed parens' % self.data.line)
            self.data.get_char()
            self.state.pop()
            if ch == ':':
                self.state.append(s.DATA)
            elif ch == '/':
                self.state.append(s.CONTENT)
            return self.get_token()
        # collect the name
        name, disallow_quotes = self._get_name(extra_terminators='=')
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
        return Token(attr_type, (name, value))

    def _get_comment(self):
        line = self.data.get_line().strip()[2:]
        line = self._consume_ws(line)
        return Token(tt.COMMENT, line)

    def _get_content(self):
        line = self.data.get_line().strip()
        return Token(tt.CONTENT, line)

    def _get_data(self):
        line = self.data.get_line().strip()
        xml_safe = True
        data_type = tt.STR_DATA
        if line[:2] == '!=':
            xml_safe = False
            data_type = tt.CODE_DATA
            line = line[2:]
        elif line[0] == '=':
            data_type = tt.CODE_DATA
            line = line[1:]
        elif line[:2] == '&=':
            data_type = tt.CODE_DATA
            line = line[2:]
        line = self._consume_ws(line)
        self.state.pop()
        return Token(data_type, line, xml_safe)

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
        name, _ = self._get_name(extra_chars='.', )
        if name in ('xml', 'xml1.0'):
            name = 'xml', '1.0'
        token = Token(tt.META, name)
        self.state.pop()
        self.state.append(s.ELEMENT)
        return token

    def _get_name(self, extra_chars=(), extra_types=(), extra_terminators=()):
        """
        gets the next name, defaults to letters, numbers, and '_' only
        extra_chars should be a sequence of actual extra allowed non-letter characters
        extra_types should be a sequence of extra unicode character types
        extra_terminators should be a sequence of extra allowed name terminators
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
            while 'collecting letters':
                uni_cat = unicodedata.category(ch)[0]
                if (uni_cat not in ('L', 'N') + tuple(extra_types) and
                    ch not in ('_', ) + tuple(extra_chars)
                    ):
                    break
                name.append(ch)
                ch = self.data.get_char()
            # valid stop chars are ' ', '\n', None, and extra_terminators
            name = ''.join(name)
            if not name:
                raise ParseError('line %d: null name not allowed' % self.data.line)
            if ch in ':/\n' or ch in extra_terminators:
                self.data.push_char(ch)
            elif ch in '(':
                self.open_parens += 1
            elif ch in ')':
                self.open_parens -= 1
                if self.open_parens < 0:
                    raise ParseError('mismatched parenthesis on line %s' % self.data.line)
            elif ch not in (' ', None):
                raise ParseError('line %d: element name %r followed by invalid char %r' %
                        (self.data.line, name, ch))
            # if ch == ' ' or ch in extra_terminators:
            #     self._consume_ws()
        return name, default

    def _get_parens(self, line):
        pass
    
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
                raise ParseError('out-of-place quote')
            quote = ch
            ch = self.data.get_char()
        while 'collecting value':
            if ch is None:
                if quote:
                    raise ParseError('unclosed quote while collecting value for %r: %r' % (''.join(value), ch))
                break
            if ch == quote:
                # skip past quote and finish
                ch = self.data.get_char()
                break
            elif quote:
                if ch == '\n':
                    if quote == '`':
                        raise ParseError('embedded newlines illegal in attribute level python code')
                    ch = ' '
                value.append(ch)
            elif ch in ('"', "'", '`'):
                raise ParseError('embedded quote')
            elif ch == '\\':
                ch = self.data.get_char()
                if ch == '\n':
                    raise ParseError('newlines cannot be escaped')
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
                raise ParseError('line %d: unbalanced parentheses' % self.data.line)
        elif ch in '(':
            self.open_parens += 1
            self._consume_ws(include='\n')
        elif ch not in (' ', '\n', ':', '/', None):
            raise ParseError('invalid character after value %r' % ''.join(value))
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
        if state == s.NORMAL:
            # looking for next whatever
            while 'nothing found yet...':
                line = self.data.peek_line()
                if line is None:
                    return self._wind_down()
                if not line.strip():
                    self.data.get_line()
                    return Token(tt.BLANK_LINE)
                    # continue
                # found something, check if indentation has changed
                last_indent = self.indents[-1]
                if not (line[:last_indent].lstrip() == '' and line[last_indent] != ' '):
                    self.state.append(s.DENTING)
                    return self._get_denting()
                else:
                    # discard white space
                    line = self.data.get_line().lstrip()
                    self.data.push_line(line)
                    ch = line[0]
                if ch == '%':
                    self.state.append(s.ELEMENT)
                    self.data.get_char()
                    return self._get_element()
                elif ch in '@#.$':
                    self.state.append(s.ELEMENT)
                    return self._get_element(default=True)
                elif line[:2] == '//':
                    return self._get_comment()
                elif line[:3] == '!!!':
                    self.state.append(tt.META)
                    return self._get_meta()
                elif ch == ':':
                    self.state.append(s.FILTER)
                    self.data.get_char()
                    return self._get_filter()
                else:
                    #must be random content
                    return self._get_content()
        elif state == s.ELEMENT:
            return self._get_attribute()
        elif state == s.DATA:
            return self._get_data()
        elif state == s.CONTENT:
            return self._get_content()
        else:
            raise ParseError('unknown state: %s' % state)


# xaml itself {{{1
class Xaml(object):

    def __init__(self, text):
        # indents tracks valid indentation levels
        self.tokens = list(Tokenizer(text))
        self.depth = [Token(None)]
        self.indents = 0
        self.encoding = 'utf-8'

    def _append_newline(self):
        if self.depth[-1].type not in (tt.INDENT, tt.BLANK_LINE):
            self.depth.append(Token(tt.BLANK_LINE))

    def _check_for_newline(self, token):
        if token.type is not tt.BLANK_LINE:
            return token, False
        else:
            return self.depth[-2], self.depth.pop()

    def parse(self, **env):
        encoding_specified = False
        output = []
        for token in self.tokens:
            last_token = self.depth and self.depth[-1] or Token(None)
            if last_token.type is tt.META:
                if token.type is tt.STR_ATTR:
                    name, value = token.payload
                    if last_token.payload[0] == 'xml':
                        if not encoding_specified and name == 'encoding':
                            encoding_specified = True
                            self.encoding = value
                    output[-1] += ' %s="%s"' % (name, value)
                    continue
                elif token.type not in (tt.CODE_ATTR, tt.STR_DATA, tt.CODE_DATA):
                    if last_token.payload[0] == 'xml' and not encoding_specified:
                        self.encoding = 'utf-8'
                        output[-1] += ' encoding="utf-8"'
                    output[-1] += '?>\n'
                    self.depth.pop()
                    if token.type is tt.DEDENT:
                        break
                else:
                    raise SystemExit('Token %s not allowed in/after META token' % token)
            elif last_token.type is tt.COMMENT:
                if token.type is not tt.COMMENT:
                    output.append('    ' * self.indents + '-->\n')
                    self.depth.pop()
                    last_token = self.depth[-1]
            if token.type in (tt.CODE_ATTR, tt.STR_ATTR):
                assert last_token.type is tt.ELEMENT, 'the tokenizer is busted'
                name, value = token.payload
                if token.type is tt.CODE_ATTR:
                    value = eval(value, env)
                if token.xml_safe:
                    value = xmlify(value)
                output[-1] += ' %s="%s"' % (name ,value)
            # COMMENT
            elif token.type is tt.COMMENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                if last_token.type is tt.ELEMENT:
                    output[-1] += '/>\n'
                    self.depth.pop()
                    if pending_newline:
                        self._append_newline()
                if pending_newline:
                    output.append('\n')
                if self.depth[-1].type is not tt.COMMENT:
                    output.append('    ' * self.indents + '<!--\n')
                    self.depth.append(token)
                output.append('    ' * self.indents + ' -- %s\n' % token.payload)
            # CONTENT
            elif token.type is tt.CONTENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                if last_token.type is tt.ELEMENT:
                    # close previous element
                    output[-1] += '/>\n'
                    self.depth.pop()
                if pending_newline:
                    output.append('\n')
                    self._append_newline()
                output.append('    ' * self.indents + '%s\n' % token.payload)
            # DATA
            elif token.type in (tt.CODE_DATA, tt.STR_DATA):
                string = '>'
                value ,= token.payload
                if token.type is tt.CODE_DATA:
                    value = eval(value, env)
                if token.xml_safe:
                    value = xmlify(value)
                token = self.depth.pop()
                string += value + '</%s>\n' % token.payload
                output[-1] += string
            # DEDENT
            elif token.type is tt.DEDENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                # need to close the immediately preceeding tag, and the
                # tags dedented to
                self.indents -= 1
                if last_token.type is tt.ELEMENT:
                    output[-1] += '/>\n'
                    self.depth.pop()
                should_be_indent = self.depth.pop()
                assert should_be_indent.type in (tt.INDENT, None), 'something broke: %s\n%s' % (should_be_indent, ''.join(output))
                try:
                    last_token = self.depth[-1]
                except IndexError:
                    # all done!
                    break
                if last_token.type is tt.BLANK_LINE:
                    output.append('\n')
                    self.depth.pop()
                    last_token = self.depth[-1]
                if last_token.type is tt.ELEMENT:
                    closing_token = self.depth.pop()
                    output.append('    ' * self.indents)
                    output[-1] += '</%s>\n' % closing_token.payload
                if pending_newline:
                    self.depth.append(pending_newline)
            # ELEMENT
            elif token.type is tt.ELEMENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                if last_token.type is tt.ELEMENT:
                    # close previous element
                    output[-1] += '/>\n'
                    self.depth.pop()
                if pending_newline:
                    output.append('\n')
                    self._append_newline()
                output.append('    ' * self.indents)
                output.append('<%s' % token.payload)
                self.depth.append(token)
            # FILTER
            elif token.type is tt.FILTER:
                name, lines = token.payload
                if name == 'python':
                    prepend = []
                    for i in range(self.indents +1):
                        prepend.append('    ' * i + 'if 1:\n')
                    lines = ''.join(prepend) + lines
                    exec(lines, env)
                else:
                    raise ParseError('unknown filter: %r' % name)
            # INDENT
            elif token.type is tt.INDENT:
                last_token, pending_newline = self._check_for_newline(last_token)
                if last_token.type is tt.ELEMENT:
                    output[-1] += '>\n'
                self.indents += 1
                if pending_newline:
                    output.append('\n')
                    self._append_newline()
                self.depth.append(token)
            # META
            elif token.type is tt.META:
                if len(self.depth) != 1 or self.depth[0].type != None:
                    raise ParseError('meta tags (such as %r) cannot be nested' % token.payload)
                name, value = token.payload
                if name == 'xml':
                    output.append('<?xml version="%s"' % value)
                else:
                    raise SystemExit('unknown META: %r' % ((name, value)))
                self.depth.append(token)
            # BLANK_LINE
            elif token.type is tt.BLANK_LINE:
                if last_token.type is tt.BLANK_LINE:
                    continue
                else:
                    self.depth.append(token)
            # problem
            else:
                raise ParseError('unknown token: %r' % token)

        return ''.join(output).encode(self.encoding)


class ParseError(Exception):
    '''
    Used for xaml parse errors
    '''

def xmlify(text):
    result = []
    for ch in text:
        if ch == '<':
            result.append('&lt;')
        elif ch == '>':
            result.append('&gt;')
        elif ch == '&':
            result.append('&amp;')
        else:
            result.append(ch)
    return ''.join(result)
