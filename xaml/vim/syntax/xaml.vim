" Vim syntax file
" Language:	Xaml
" Maintainer:	Ethan Furam <ethanNULL@stoneleaf.us>
" Filenames:	*.xaml
" Last Change:	2015 Jan 02

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
"syn case match
syn match xamlTag "\~\w\+" contained
syn match xamlClass "\.\w[^:!"#$%&'()*+,/;<=>?@[\]^`{|}~ ]*" contained
syn match xamlId "#\w[^:!"#$%&'()*+,/;<=>?@[\]^`{|}~ ]*" contained
syn match xamlString "$\w[^:!"#$%&'()*+,/;<=>?@[\]^`{|}~ ]*" contained
syn match xamlName "@\w[^:!"#$%&'()*+,/;<=>?@[\]^`{|}~ ]*" contained

syn match xamlPython "`[^`]*`" contains=@xamlPythonTop

syn region xamlAttributeSQuote start=+'+ skip=+\%(\\\\\)*\\'+ end=+'+ contained keepend
syn region xamlAttributeDQuote start=+"+ skip=+\%(\\\\\)*\\"+ end=+"+ contained keepend
syn region xamlLine start="\(^\s*\)\@<=[~.#$@]" end="[/\]:\n]" contains=xamlTag,xamlClass,xamlId,xamlString,xamlName,xamlAttributeSQuote,xamlAttributeDQuote
"
"syn cluster xamlComponent    contains=xamlBegin,xamlClassChar,xamlIdChar,xamlNameChar,xamlStringChar,xamlPython,xamlPlainChar,xamlInterpolatable
"syn cluster xamlEmbeddedPython contains=xamlPython,xamlPythonFilter,xamlPythonTickQuote
""syn cluster xamlTop          contains=xamlBegin,xamlPlainFilter,xamlPythonFilter,xamlSassFilter,xamlComment,xamlHtmlComment
"
"syn match   xamlData "\v:.*$"
"syn match   xamlBegin "\v^\s*\~" nextgroup=xamlTag ",xamlClassChar,xamlIdChar,xamlPython,xamlPlainChar,xamlInterpolatable
"
"syn region  xmalElement matchgroup=xamlAttributesDelimiter start='\v[%.#@$]' end='\v(:|$)' nextgroup=xamlData
""syn region  xamlAttributesHash matchgroup=xamlAttributesDelimiter start="{" end="}" contained contains=@xamlPythonTop nextgroup=@xamlComponent
syn region  xamlDocType start="^!!!" end="$"
"
"syn region  xamlPython   matchgroup=xamlPythonOutputChar start="\v[!&]=\=" end="$" contained contains=@xamlPythonTop keepend
syn region  xamlPython  start="^\z(\s*\)-"  end="$" transparent contains=@xamlPythonTop
"syn match   xamlPlainChar "\\" contained
""syn region xamlInterpolatable matchgroup=xamlInterpolatableChar start="!\===\|!=\@!" end="$" keepend contained contains=xamlInterpolation,xamlInterpolationEscape,@xamlHtmlTop
""syn region xamlInterpolatable matchgroup=xamlInterpolatableChar start="&==\|&=\@!"   end="$" keepend contained contains=xamlInterpolation,xamlInterpolationEscape
""syn region xamlInterpolation matchgroup=xamlInterpolationDelimiter start="#{" end="}" contains=@xamlPythonTop containedin=javascriptStringS,javascriptStringD
""syn match  xamlInterpolationEscape "\\\@<!\%(\\\\\)*\\\%(\\\ze#{\|#\ze{\)"
"
"syn match   xamlPythonTickQuote "\v\`[^`]*\`"
"syn match   xamlAttributeVariable "\%(=\s*\)\@<=\%(@@\=\|\$\)\=\w\+" contained
"
"syn match   xamlHelper  "\<action_view?\|\<block_is_xaml?\|\<is_xaml?\|\.\@<!\<flatten" contained containedin=@xamlEmbeddedPython,@xamlPythonTop
""syn keyword xamlHelper   capture_xaml escape_once find_and_preserve xaml_concat xaml_indent xaml_tag html_attrs html_esape init_xaml_helpers list_of non_xaml precede preserve succeed surround tab_down tab_up page_class contained containedin=@xamlEmbeddedPython,@xamlPythonTop
"
""syn cluster xamlHtmlTop contains=@htmlTop,htmlBold,htmlItalic,htmlUnderline
"syn region  xamlPlainFilter      matchgroup=xamlFilter start="^\z(\s*\):\%(plain\|preserve\|redcloth\|textile\|markdown\|maruku\)\s*$" end="^\%(\z1 \| *$\)\@!" contains=@xamlHtmlTop,xamlInterpolation
"syn region  xamlEscapedFilter    matchgroup=xamlFilter start="^\z(\s*\):\%(escaped\|cdata\)\s*$"    end="^\%(\z1 \| *$\)\@!" contains=xamlInterpolation
syn region  xamlPythonFilter      matchgroup=xamlFilter start="^\z(\s*\):python\s*$"       end="^\%(\z1 \| *$\)\@!" contains=@xamlPythonTop keepend
syn region  xamlJavascriptFilter  matchgroup=xamlFilter start="^\z(\s*\):javascript\s*$"   end="^\%(\z1 \| *$\)\@!" contains=@xamlJavaScriptTop keepend
syn region  xamlCSSFilter         matchgroup=xamlFilter start="^\z(\s*\):css\s*$"          end="^\%(\z1 \| *$\)\@!" contains=@xamlCssTop keepend
syn region  xamlCDataPythonFilter matchgroup=xamlFilter start="^\z(\s*\):cdata-python\s*$" end="^\%(\z1 \| *$\)\@!" contains=@xamlPythonTop keepend
syn region  xamlCDataFilter       matchgroup=xamlFilter start="^\z(\s*\):cdata\s*$"        end="^\%(\z1 \| *$\)\@!"
"
"syn match   xamlError "\$" contained
"
syn region  xamlComment     start="^\z(\s*\)//" end="\n" contains=pythonTodo
"syn region  xamlHtmlComment start="^\z(\s*\)/"  end="^\%(\z1 \| *$\)\@!" contains=@xamlTop,pythonTodo
"syn match   xamlIEConditional "\%(^\s*/\)\@<=\[if\>[^]]*]" contained containedin=xamlHtmlComment

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
