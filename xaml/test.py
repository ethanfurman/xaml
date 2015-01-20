from __future__ import unicode_literals
from unittest import TestCase, main
from textwrap import dedent
import xaml
from xaml import Xaml, PPLCStream, Token, Tokenizer, TokenType, State

s = State
tt = TokenType


class TestXaml(TestCase):

    maxDiff = None

    def test_meta_coding(self):
        result = Xaml('!!! coding: cp1252\n!!! xml'.encode('cp1252')).parse()
        expected = '<?xml version="1.0" encoding="utf-8"?>\n'
        self.assertEqual(expected, result)

    def test_1(self):
        input = dedent('''
            %opentag
                %level_one
                    %field @code: Code goes here
            ''')
        expected = dedent('''\
            <opentag>
                <level_one>
                    <field name="code">Code goes here</field>
                </level_one>
            </opentag>
            '''.encode('utf-8'))
        self.assertEqual(expected, Xaml(input).parse())

    def test_2(self):

        input = dedent('''
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
        expected = dedent('''\
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
            '''.encode('utf-8'))
        self.assertEqual(expected, Xaml(input).parse())

    def test_meta_closing(self):
        result = Xaml('!!! xml1.0').parse()
        self.assertEqual(
                '<?xml version="1.0" encoding="utf-8"?>\n'.encode('utf-8'),
                result,
                )

    def test_meta_xml_version(self):
        result = Xaml('!!! xml1.0 encoding="cp1252"').parse()
        self.assertEqual(
                '<?xml version="1.0" encoding="cp1252"?>\n'.encode('utf-8'),
                result,
                )

    def test_element_closing(self):
        result = Xaml('%opentag').parse()
        self.assertEqual(
                '<opentag/>\n'.encode('utf-8'),
                result,
                )

    def test_filter(self):
        input = dedent('''
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
            '''.encode('utf-8'))
        self.assertEqual(expected, Xaml(input).parse())

    def test_filter_2(self):
        input = dedent('''
            :python
                view = 'ir.ui.view'
                folder_model = 'fnx.fs.folder'
                files_model = 'fnx.fs.file'
                action = 'ir.actions.act_window'

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
                                @description
                    %record model=action #action_fnx
                        @name: An Action
                        @res_model: = folder_model
                        @view_type: form
                        @view_id ref='something'
                        @view_mode: form,tree''')
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
                    <record model="ir.actions.act_window" id="action_fnx">
                        <field name="name">An Action</field>
                        <field name="res_model">fnx.fs.folder</field>
                        <field name="view_type">form</field>
                        <field name="view_id" ref="something"/>
                        <field name="view_mode">form,tree</field>
                    </record>
                </data>
            </openerp>
            '''.encode('utf-8'))
        self.assertEqual(expected, Xaml(input).parse())

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

    def test_error(self):
        self.assertRaises(SystemExit, PPLCStream, b'!!! coding: blah')
        self.assertRaises(SystemExit, PPLCStream, b'!!! coding:')


class TestTokenizer(TestCase):

    maxDiff = None

    def test_tokens_1(self):
        result = list(Tokenizer('       '))
        self.assertEqual(result, [Token(tt.DEDENT)])

    def test_tokens_2(self):
        result = list(Tokenizer('   !!! xml\n'))
        self.assertEqual(
            [
                Token(tt.INDENT),
                Token(tt.META, ('xml', '1.0')),
                Token(tt.DEDENT),
                Token(tt.DEDENT),
            ],
            result,
            )
        self.assertEqual(None, result[0].payload)


    def test_tokens_3(self):
        result = list(Tokenizer('%opentag\n  %level_one\n    %field @code: Code goes here'))
        self.assertEqual(
            [
                Token(tt.ELEMENT, 'opentag'),
                Token(tt.INDENT),
                Token(tt.ELEMENT, 'level_one'),
                Token(tt.INDENT),
                Token(tt.ELEMENT, 'field'),
                Token(tt.STR_ATTR, ('name', 'code')),
                Token(tt.STR_DATA, 'Code goes here', xml_safe=True),
                Token(tt.DEDENT),
                Token(tt.DEDENT),
                Token(tt.DEDENT),
            ],
            result,
            )

    def test_tokens_4(self):
        result = list(Tokenizer('!!! xml\n:python\n  view="ir.ui.view"\n  model="some_test.my_table"\n%openerp\n  %record #some_id model=view\n    @name: Folders\n    @arch type="xml"\n'))
        self.assertEqual(
            [
                Token(TokenType.META, payload=('xml', '1.0')),
                Token(tt.FILTER, ('python', '  view="ir.ui.view"\n  model="some_test.my_table"\n')),
                Token(tt.ELEMENT, 'openerp'),
                Token(tt.INDENT),
                Token(tt.ELEMENT, 'record'),
                Token(tt.STR_ATTR, ('id', 'some_id')),
                Token(tt.CODE_ATTR, ('model', 'view')),
                Token(tt.INDENT),
                Token(tt.ELEMENT, 'field'),
                Token(tt.STR_ATTR, ('name', 'name')),
                Token(tt.STR_DATA, 'Folders', True),
                Token(tt.ELEMENT, 'field'),
                Token(tt.STR_ATTR, ('name', 'arch')),
                Token(tt.STR_ATTR, ('type', 'xml')),
                Token(tt.DEDENT),
                Token(tt.DEDENT),
                Token(tt.DEDENT),
            ],
            result,
            )

    def test_tokens_5(self):
        result = list(xaml.Tokenizer(dedent('''
        !!! xml
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
                Token(TokenType.META, payload=('xml', '1.0')),
                Token(TokenType.ELEMENT, payload='openerp'),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload='record'),
                Token(TokenType.STR_ATTR, payload=('id', 'fax_id')),
                Token(TokenType.STR_ATTR, payload=('view', 'ui.ir.view')),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload='field'),
                Token(TokenType.STR_ATTR, payload=('name', 'name')),
                Token(TokenType.STR_DATA, payload='Folders', xml_safe=True),
                Token(TokenType.ELEMENT, payload='field'),
                Token(TokenType.STR_ATTR, payload=('name', 'arch')),
                Token(TokenType.STR_ATTR, payload=('type', 'xml')),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload='form'),
                Token(TokenType.STR_ATTR, payload=('string', 'Folders')),
                Token(TokenType.STR_ATTR, payload=('version', '7.0')),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload='group'),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload='group'),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload='field'),
                Token(TokenType.STR_ATTR, payload=('name', 'id')),
                Token(TokenType.STR_ATTR, payload=('invisibility', '1')),
                Token(TokenType.ELEMENT, payload='field'),
                Token(TokenType.STR_ATTR, payload=('name', 'name')),
                Token(TokenType.ELEMENT, payload='field'),
                Token(TokenType.STR_ATTR, payload=('name', 'path')),
                Token(TokenType.DEDENT),
                Token(TokenType.ELEMENT, payload='group'),
                Token(TokenType.INDENT),
                Token(TokenType.ELEMENT, payload='field'),
                Token(TokenType.STR_ATTR, payload=('name', 'folder_type')),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
                Token(TokenType.DEDENT),
                Token(tt.DEDENT),
            ],
            result,
            )

    def test_meta_token(self):
        result = list(xaml.Tokenizer('!!! xml1.0'))
        self.assertEqual(
            [
                Token(tt.META, ('xml', '1.0')),
                Token(tt.DEDENT),
            ],
            result,
            )

    def test_string_tokens(self):
        result = list(xaml.Tokenizer('%test_tag $This_could_be_VERY_cool!'))
        self.assertEqual(
            [
                Token(tt.ELEMENT, 'test_tag'),
                Token(tt.STR_ATTR, ('string', 'This could be VERY cool!')),
                Token(tt.DEDENT),
            ],
            result,
            )

    def test_code_data(self):
        result = list(xaml.Tokenizer('%top_tag\n  %record_tag\n    @Setting: = a_var'))
        self.assertEqual(
            [
                Token(tt.ELEMENT, 'top_tag'),
                Token(tt.INDENT),
                Token(tt.ELEMENT, 'record_tag'),
                Token(tt.INDENT),
                Token(tt.ELEMENT, 'field'),
                Token(tt.STR_ATTR, ('name', 'Setting')),
                Token(tt.CODE_DATA, 'a_var', xml_safe=True),
                Token(tt.DEDENT),
                Token(tt.DEDENT),
                Token(tt.DEDENT),
            ],
            result,
            )


if __name__ == '__main__':
    main()
