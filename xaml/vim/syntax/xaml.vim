" Vim syntax file
" Language:	Xaml
" Maintainer:	Ethan Furam <ethanNULL@stoneleaf.us>
" Filenames:	*.xaml
" Last Change:	2016 Jan 15

if exists("b:current_syntax")
  finish
endif

if !exists("main_syntax")
  let main_syntax = 'xaml'
endif
let b:python_no_expensive = 1

syn include @xamlPythonTop syntax/python.vim
syn include @xamlJavaScriptTop syntax/javascript.vim
syn include @xamlCSSTop syntax/css.vim
"
syn match xamlTag "\~\w\+" contained
syn match xamlClass "\.\w\+" contained
syn match xamlId "#\w\+" contained
syn match xamlString "$\w\+" contained
syn match xamlName "@\w\+" contained
"
syn match xamlPython "`[^`]*`" contains=@xamlPythonTop
"
syn region xamlAttributeSQuote start=+'+ skip=+\%(\\\\\)*\\'+ end=+'+ contained keepend
syn region xamlAttributeDQuote start=+"+ skip=+\%(\\\\\)*\\"+ end=+"+ contained keepend
syn region xamlLine start="\(^\s*\)\@<=[~.#$@]" end="[/\]:\n]" contains=xamlTag,xamlClass,xamlId,xamlString,xamlName,xamlAttributeSQuote,xamlAttributeDQuote
"
syn region  xamlDocType start="^!!!" end="$"
"
syn region  xamlPython  start="^\z(\s*\)-"  end="$" transparent contains=@xamlPythonTop
syn region  xamlPythonFilter      matchgroup=xamlFilter start="^\z(\s*\):python\s*$"       end="^\%(\z1 \| *$\)\@!" contains=@xamlPythonTop keepend
syn region  xamlJavascriptFilter  matchgroup=xamlFilter start="^\z(\s*\):javascript\s*$"   end="^\%(\z1 \| *$\)\@!" contains=@xamlJavaScriptTop keepend
syn region  xamlCSSFilter         matchgroup=xamlFilter start="^\z(\s*\):css\s*$"          end="^\%(\z1 \| *$\)\@!" contains=@xamlCssTop keepend
syn region  xamlCDataPythonFilter matchgroup=xamlFilter start="^\z(\s*\):cdata-python\s*$" end="^\%(\z1 \| *$\)\@!" contains=@xamlPythonTop keepend
syn region  xamlCDataFilter       matchgroup=xamlFilter start="^\z(\s*\):cdata\s*$"        end="^\%(\z1 \| *$\)\@!"
"
syn region  xamlComment     start="^\z(\s*\)//" end="\n" contains=pythonTodo
"
hi def link xamlTag                    Special
hi def link xamlName                   SpecialFour
hi def link xamlString                 SpecialOne
hi def link xamlClass                  SpecialThree
hi def link xamlId                     SpecialTwo
hi def link xamlLine                   SpecialFive
hi def link xamlPlainChar              Special
hi def link xamlInterpolatableChar     xamlPythonChar
hi def link xamlPythonOutputChar       xamlPythonChar
hi def link xamlPythonChar             Special
hi def link xamlInterpolationDelimiter Delimiter
hi def link xamlInterpolationEscape    Special
hi def link xamlPython                 xamlPythonChar
hi def link xamlAttributeSQuote        xamlQuote
hi def link xamlAttributeDQuote        xamlQuote
hi def link xamlAttributeVariable      Identifier
hi def link xamlDocType                PreProc
hi def link xamlFilter                 PreProc
hi def link xamlAttributesDelimiter    Delimiter
hi def link xamlHelper                 Function
hi def link xamlHtmlComment            xamlComment
hi def link xamlComment                Comment
hi def link xamlIEConditional          SpecialComment
hi def link xamlError                  Error

let b:current_syntax = "xaml"

if main_syntax == "xaml"
  unlet main_syntax
endif

" vim:set sw=2:
