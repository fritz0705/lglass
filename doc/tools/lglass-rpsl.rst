:program:`lglass-rpsl` – RPSL object format parser
==================================================

The :program:`lglass-rpsl` tool is a simple RPSL object formatter. It supports
several options for padding and parsing of object files, including pragma
selection. By default, it reads the standard input and writes the formatted
object to standard output, but is also capable of doing inplace changes by
using the `-i` command line option.

::

  usage: lglass-rpsl [-h] [--padding PADDING] [--inplace INPLACE [INPLACE ...]]
                     [--whitespace-preserve] [--stop-at-empty-line]
                     [--condense-whitespace] [--validate] [--database DATABASE]

  Simple tool for RPSL formatting

  optional arguments:
    -h, --help            show this help message and exit
    --padding PADDING, -p PADDING
                          Define whitespace padding between key and value
    --inplace INPLACE [INPLACE ...], -i INPLACE [INPLACE ...]
                          Change the RPSL files in-place
    --whitespace-preserve
                          Turn the whitespace-preserve pragma on
    --stop-at-empty-line  Turn the stop-at-empty-line pragma on
    --condense-whitespace
                          Turn the condense-whitespace pragma on
    --validate, -V        Validate RPSL against schema
    --database DATABASE, -D DATABASE
                          Database for schema files
