xaml -- XML Abstract Markup Language
====================================

an easier way for humans to write xml and html

if a line starts with any xaml component ( ~ @ . # $ ) that line represents
an xml/http element::

  - an element continues until eol, or an unquoted :
  - an element can be continued to the next line(s) using unquoted parens

if a line starts with a ":" it is specifying how the following lines should
be interpreted::

  - :css -> cascading style sheets that are inserted with a <style> tag

  - :python -> python code inserted into a <script type="text/python"> tag
               (must have a python interpreter running in the browser; e.g.
               Brython (http://brython.info/index.html))

  - :javascript -> javascript code inserted into a
                   <script type="text/javascript"> tag

  - :cdata -> contained lines are placed in <![CDATA[ and ]]> tags

if a line starts with // it is a comment, and will be converted into an
xml/html comment

if a line starts with a "-" (hyphen) it is a single line of Python code that
will be run to help generate the final output

otherwise the line represents the content of an element

xaml components::

  - ~ -> element name
  - @ -> name attribute
  - . -> class attribute
  - # -> id attribute
  - $ -> string attribute

    e.g. ~document .bold #doc_1 @AutoBiography $My_Biography ->

    <document class="bold" id="doc_1" name="AutoBiography" string="My Biography"/>

Based on haml [1] but aimed at Python.

Still in its early stages -- send email to ethan at stoneleaf dot us if you
would like to get involved!

Mercurial repository, wiki, and issue tracker at [2].


[1] http://haml.info/
[2] https://bitbucket.org/stoneleaf/xaml
