from distutils.core import setup
import sys

long_desc = '''\
xaml -- XML Abstract Markup Language
====================================

an easier way for humans to write xml and html

if a line starts with any xaml component ( % @ . # $ ) that line represents
an xml/http element::

  - an element continues until eol, or an unquoted :
  - an element can be continued to the next line(s) using unquoted parens

elif a line starts with a ":" it is specifying how the following lines should
be interpreted::

  - :markdown -> markdown text (not implemented)
  - :python -> python code (implemented)

elif a line starts with // it is a comment, and will be converted into an
xml/html comment

elif a line starts with a "-" it is a single line of Python code that will
be run to help generate the final output

else the line represents the content of an element

xaml components::

  - % -> element name
  - @ -> name attribute
  - . -> class attribute
  - # -> id attribute
  - $ -> string attribute (_ to ' ' conversion not implemented)

    e.g. %document .bold #doc_1 @AutoBiography $My_Biography ->

    <document class="bold" id="doc_1" name="AutoBiography" string="My Biography"/>

Based on haml [1] but aimed at Python.

Still in its early stages -- send email to ethan at stoneleaf dot us if you
would like to get involved!

Mercurial repository, wiki, and issue tracker at [2].


[1] http://haml.info/
[2] https://bitbucket.org/stoneleaf/xaml
'''

requirements = ['antipathy', 'scription']
if sys.version_info < (3, 4):
    requirements.append('enum34')
elif sys.version_info < (3, 3):
    raise ValueError("Xaml requires at Python 2.7 or 3.3+")

setup( name='xaml',
       version= '0.4.8',
       license='BSD License',
       description='XML Abstract Markup Language',
       long_description=long_desc,
       packages=['xaml'],
       package_data={'xaml':['CHANGES', 'LICENSE', 'README']},
       install_requires=requirements,
       author='Ethan Furman',
       author_email='ethan@stoneleaf.us',
       url='https://bitbucket.org/stoneleaf/xaml',
       classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Topic :: Software Development',
            'Topic :: Text Processing :: Markup :: HTML',
            'Topic :: Text Processing :: Markup :: XML',
            ],
    )

