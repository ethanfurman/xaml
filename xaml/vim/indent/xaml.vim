" Vim indent file
" Language:	Xaml
" Maintainer:	Ethan Furman <ethanNULL@stoneleaf.us>
" Last Change:	2015 Jan 02

if exists("b:did_indent")
  finish
endif
runtime! indent/python.vim
unlet! b:did_indent
let b:did_indent = 1

setlocal autoindent expandtab smartindent tabstop=4 softtabstop=4 shiftwidth=4
setlocal indentexpr=GetXamlIndent()
setlocal indentkeys=o,O,*<Return>,],0),!^F,=end,=else,=elsif,=rescue,=ensure,=when

" Only define the function once.
if exists("*GetXamlIndent")
  finish
endif

let s:attributes = '\%({.\{-\}}\|\[.\{-\}\]\)'
let s:tag = '\%([%.#][[:alnum:]_-]\+\|'.s:attributes.'\)*[<>]*'

if !exists('g:xaml_self_closing_tags')
  let g:xaml_self_closing_tags = 'meta|link|img|hr|br'
endif

function! GetXamlIndent()
  let lnum = prevnonblank(v:lnum-1)
  if lnum == 0
    return 0
  endif
  let line = substitute(getline(lnum),'\s\+$','','')
  let cline = substitute(substitute(getline(v:lnum),'\s\+$','',''),'^\s\+','','')
  let lastcol = strlen(line)
  let line = substitute(line,'^\s\+','','')
  let indent = indent(lnum)
  let cindent = indent(v:lnum)
  if cline =~# '\v^-\s*%(elsif|else|when)>'
    let indent = cindent < indent ? cindent : indent - &sw
  endif
  let increase = indent + &sw
  if indent == indent(lnum)
    let indent = cindent <= indent ? -1 : increase
  endif

  let group = synIDattr(synID(lnum,lastcol,1),'name')

  if line =~ '^!!!'
    return indent
  "elseif line =~ '^/\%(\[[^]]*\]\)\=$'
  "  return increase
  elseif group == 'xamlFilter'
    return increase
  elseif line =~ '^'.s:tag.'[&!]\=[=~-]\s*\%(\%(if\|else\|elif\|while\|for\|class\|def\|try\|except\|finally\)\>\%(.*\<\(break\|return\)\>\)\@!\)'
    return increase
  elseif line =~ '^'.s:tag.'[&!]\=[=~-].*,\s*$'
    return increase
  elseif line == '-#'
    return increase
  elseif group =~? '\v^(xamlSelfCloser)$' || line =~? '^%\v%('.g:xaml_self_closing_tags.')>'
    return indent
  elseif group =~? '\v^%(xamlTag|xamlAttributesDelimiter|xamlObjectDelimiter|xamlClass|xamlId|htmlTagName|htmlSpecialTagName)$'
    return increase
  elseif synIDattr(synID(v:lnum,1,1),'name') ==? 'xamlPython'
    return GetPython()
  else
    return indent
  endif
endfunction

" vim:set sw=2:
