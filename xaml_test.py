from unittest import TestCase, main
from textwrap import dedent
import xaml
from xaml import Xaml, PPLCStream, Token, Tokenizer, TokenType, State

s = State
tt = TokenType


class TestXaml(TestCase):

    maxDiff = None

    def test_1(self):
        input = dedent(u'''
            %opentag
                %level_one
                    %field @code: Code goes here
            ''')
        expected = dedent(u'''\
            <opentag>
                <level_one>
                    <field name="code">Code goes here</field>
                </level_one>
            </opentag>
            ''')
        self.assertEqual(Xaml(input).parse(), expected)

    def test_2(self):

        input = dedent(u'''
             %openerp
                %record #fax_id view='ui.ir.view'
                   @name: Folders
                   @arch type='xml'
                      %form $Folders version='7.0'
                         %group
                            %group
                               @id invisibility='1'
                               @name
                               @path
                            %group
                               @folder_type''')
        expected = dedent(u'''\
            <openerp>
                <record id="fax_id" view="ui.ir.view">
                    <field name="name">Folders</field>
                    <field name="arch" type="xml">
                        <form string="Folders" version="7.0">
                            <group>
                                <group>
                                    <field name="id" invisibility="1"/>
                                    <field name="name"/>
                                    <field name="path"/>
                                </group>
                                <group>
                                    <field name="folder_type"/>
                                </group>
                            </group>
                        </form>
                    </field>
                </record>
            </openerp>
            ''')
        self.assertEqual(Xaml(input).parse(), expected)

    def test_filter(self):
        input = dedent(u'''
            :python
                view = 'ir.ui.view'
                folder_model = 'fnx.fs.folder'
                files_model = 'fnx.fs.file'
                

            %openerp

                %data

                    %menuitem @FnxFS #fnx_file_system groups='consumer'

                    %record #fnx_fs_folders_tree model=view
                        @name: Folders
                        @model: =folder_model
                        @arch type='xml'
                            %tree $Folders version='7.0'
                                @path
                                @folder_type
                                @description ''')
        expected = dedent('''\
            <openerp>
                <data>
                    <menuitem name="FnxFS" id="fnx_file_system" groups="consumer"/>
                    <record id="fnx_fs_folders_tree" model="ir.ui.view">
                        <field name="name">Folders</field>
                        <field name="model">fnx.fs.folder</field>
                        <field name="arch" type="xml">
                            <tree string="Folders" version="7.0">
                                <field name="path"/>
                                <field name="folder_type"/>
                                <field name="description"/>
                            </tree>
                        </field>
                    </record>
                </data>
            </openerp>
            ''')
        self.assertEqual(Xaml(input).parse(), expected)

class TestPPLCStream(TestCase):

    def test_get_char(self):
        sample = 'line one\nline two\n'
        stream = PPLCStream(sample)
        result = []
        while True:
            ch = stream.get_char()
            if ch is None:
                break
            result.append(ch)
        self.assertEqual(''.join(result), sample)

    def test_get_line(self):
        sample = 'line one\nline two\n'
        stream = PPLCStream(sample)
        result = []
        while True:
            line = stream.get_line()
            if line is None:
                break
            result.append(line)
        self.assertEqual(''.join(result), sample)

    def test_push_char(self):
        sample = 'line one\nline two\n'
        stream = PPLCStream(sample)
        result = []
        stream.push_char('2')
        stream.push_char('4')
        while True:
            line = stream.get_line()
            if line is None:
                break
            result.append(line)
        self.assertEqual(''.join(result), '42' + sample)

    def test_push_line(self):
        sample = 'line one\nline two\n'
        stream = PPLCStream(sample)
        result = []
        stream.push_line('line zero')
        while True:
            ch = stream.get_char()
            if ch is None:
                break
            result.append(ch)
        self.assertEqual(''.join(result), 'line zero\n' + sample)


class TestTokenizer(TestCase):

    maxDiff = None

    def test_tokens_1(self):
        text = '!!! strict'
        result = list(Tokenizer('       '))
        self.assertEqual(result, [])

    def test_tokens_2(self):
        result = list(Tokenizer(u'   !!!\n'))
        self.assertEqual(Token(tt.INDENT), result[0])
        self.assertEqual([Token(tt.INDENT), Token(tt.META, '!!!')], result)
        self.assertEqual(None, result[0].payload)
        self.assertEqual('!!!', result[1].payload)

    def test_tokens_3(self):
        result = list(Tokenizer(u'%opentag\n  %level_one\n    %field @code: Code goes here'))
        self.assertEqual(
            [
                Token(tt.ELEMENT, u'opentag'),
                Token(tt.INDENT),
                Token(tt.ELEMENT, u'level_one'),
                Token(tt.INDENT),
                Token(tt.ELEMENT, u'field'),
                Token(tt.STR_ATTR, (u'name', u'code')),
                Token(tt.STR_DATA, u'Code goes here', xml_safe=True),
                Token(tt.DEDENT),
                Token(tt.DEDENT),
            ],
            result,
            )

    def test_tokens_4(self):
        result = list(Tokenizer(':python\n  view="ir.ui.view"\n  model="some_test.my_table"\n%openerp\n  %record #some_id model=view\n    @name: Folders\n    @arch type="xml"\n'))
        self.assertEqual(
            [
                Token(tt.FILTER, (u'python', u'  view="ir.ui.view"\n  model="some_test.my_table"\n')),
                Token(tt.ELEMENT, u'openerp'),
                Token(tt.INDENT),
                Token(tt.ELEMENT, u'record'),
                Token(tt.STR_ATTR, (u'id', u'some_id')),
                Token(tt.CODE_ATTR, (u'model', u'view')),
                Token(tt.INDENT),
                Token(tt.ELEMENT, u'field'),
                Token(tt.STR_ATTR, (u'name', u'name')),
                Token(tt.STR_DATA, u'Folders', True),
                Token(tt.ELEMENT, u'field'),
                Token(tt.STR_ATTR, (u'name', u'arch')),
                Token(tt.STR_ATTR, (u'type', u'xml')),
                Token(tt.DEDENT),
                Token(tt.DEDENT),
            ],
            result,
            )

    def test_token_5(self):
        result = list(xaml.Tokenizer(dedent(u'''
        %openerp
           %record #fax_id view='ui.ir.view'
              @name: Folders
              @arch type='xml'
                 %form $Folders version='7.0'
                    %group
                       %group
                          @id invisibility='1'
                          @name
                          @path
                       %group
                          @folder_type
        ''')))
        self.assertEqual(
            [
                Token(TokenType.ELEMENT, payload=u'openerp'),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload=u'record'),
                Token(TokenType.STR_ATTR, payload=(u'id', u'fax_id')),
                Token(TokenType.STR_ATTR, payload=(u'view', u'ui.ir.view')),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload=u'field'),
                Token(TokenType.STR_ATTR, payload=(u'name', u'name')),
                Token(TokenType.STR_DATA, payload=u'Folders', xml_safe=True),
                Token(TokenType.ELEMENT, payload=u'field'),
                Token(TokenType.STR_ATTR, payload=(u'name', u'arch')),
                Token(TokenType.STR_ATTR, payload=(u'type', u'xml')),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload=u'form'),
                Token(TokenType.STR_ATTR, payload=(u'string', u'Folders')),
                Token(TokenType.STR_ATTR, payload=(u'version', u'7.0')),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload=u'group'),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload=u'group'),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload=u'field'),
                Token(TokenType.STR_ATTR, payload=(u'name', u'id')),
                Token(TokenType.STR_ATTR, payload=(u'invisibility', u'1')),
                Token(TokenType.ELEMENT, payload=u'field'),
                Token(TokenType.STR_ATTR, payload=(u'name', u'name')),
                Token(TokenType.ELEMENT, payload=u'field'),
                Token(TokenType.STR_ATTR, payload=(u'name', u'path')),
                Token(TokenType.DEDENT),
                Token(TokenType.ELEMENT, payload=u'group'),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload=u'field'),
                Token(TokenType.STR_ATTR, payload=(u'name', u'folder_type')),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
            ],
            result,
            )

    def test_string_tokens(self):
        result = list(xaml.Tokenizer('%test_tag $This_could_be_VERY_cool!'))
        self.assertEqual(
            [
                Token(tt.ELEMENT, u'test_tag'),
                Token(tt.STR_ATTR, (u'string', u'This could be VERY cool!')),
            ],
            result,
            )

if __name__ == '__main__':
    main()
