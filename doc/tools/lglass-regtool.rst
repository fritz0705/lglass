:program:`lglass-regtool` – Registry maintenance tool
=====================================================

:program:`lglass-regtool` provides a simple interface for registry database
maintenance. It consists of multiple subcommands to create, change, update and
delete resources.

::

  usage: lglass-regtool [-h] [--config CONFIG] [--editor EDITOR]
                        [--database DATABASE]
                        
                        {help,create-object,show-object,validate-object,edit-object,delete-object,list-objects,find-objects,find-inverse,format-object,whoisd,roagen,install-schemas}
                        ...

  Registry management tool

  positional arguments:
    {help,create-object,show-object,validate-object,edit-object,delete-object,list-objects,find-objects,find-inverse,format-object,whoisd,roagen,install-schemas}
                          Command to execute
      help                Print help message
      create-object       Create object in registry
      show-object         Show object in registry
      validate-object     Validate object in registry
      edit-object         Edit object in registry
      delete-object       Delete object in registry
      list-objects        List objects
      find-objects        Find objects
      find-inverse        Find inverse objects by schema
      format-object       Reformat object
      whoisd              Run whois server
      roagen              Generate ROA tables
      install-schemas     Install default schemas

  optional arguments:
    -h, --help            show this help message and exit
    --config CONFIG, -c CONFIG
                          Configuration file
    --editor EDITOR, -e EDITOR
                          Editor (e.g. vim, nano)
    --database DATABASE, -D DATABASE
                          Optional url to database

Configuration
-------------

lglass-regtool loads its configuration by default from a file called `.lglassrc`.
This can be changed by using the `--config` command line option.

The configuration format is JSON and can contain the database URL specification.
By default, lglass-regtool will use the current working directory as database
basepath.

Creating objects
----------------

Objects are created by using the `create-object` subcommand. This subcommand
takes the type and the primary key of the new object and also takes a list of 
key-value-pairs.

::

  usage: lglass-regtool create-object [-h] [--fill] [--no-fill] [--edit]
                                      [--no-edit] [--validate] [--no-validate]
                                      type primary_key [kvpairs [kvpairs ...]]

  positional arguments:
    type
    primary_key
    kvpairs        List of key-value-pairs

  optional arguments:
    -h, --help     show this help message and exit
    --fill         Prefill required fields with placeholders
    --no-fill      Do not prefill required fields with placeholders
    --edit         Start editor after creation
    --no-edit      Do not start editor after creation
    --validate     Validate object before save
    --no-validate  Do not validate object before save

Displaying objects
------------------

Objects are displayed by using the `show-object` subcommand. This will print the
object in a well-formatted fashion.

::

  usage: lglass-regtool show-object [-h] [--padding PADDING] type primary_key

  positional arguments:
    type
    primary_key

  optional arguments:
    -h, --help            show this help message and exit
    --padding PADDING, -p PADDING
                          Padding between key and value

Validating objects
------------------

Objects are validated by using the `validate-object` subcommand. This will
validate the object against the schemas of the current database and set the
appropriate exit code: 0 if the object is valid, 1 if the object is invalid, or
111 if the object was not found.

::

  usage: lglass-regtool validate-object [-h] type primary_key

  positional arguments:
    type
    primary_key

  optional arguments:
    -h, --help   show this help message and exit

Editing objects
---------------

Objects are edited by using the `edit-object` subcommand. This will load the
object and present it in an editor. After closing the editor it will be saved
in a well-formatted fashion.

::

  usage: lglass-regtool edit-object [-h] [--validate] [--no-validate]
                                    type primary_key

  positional arguments:
    type
    primary_key

  optional arguments:
    -h, --help     show this help message and exit
    --validate     Validate object before save
    --no-validate  Do not validate object before save

Deleting objects
----------------

Objects are deleted by using the `delete-object` subcommand. This subcommand
takes the type and the primary key of an object and deletes it in the database.

::

  usage: lglass-regtool delete-object [-h] type primary_key

  positional arguments:
    type
    primary_key

  optional arguments:
    -h, --help   show this help message and exit

Listing objects
---------------

To obtain a listing of objects there is the `list-objects` subcommand. This
subcommand takes the optional `--type TYPES` argument to subset the returned
object types. It prints a listing of objects separated by newlines, where the
type and primary key are separated by tabs.

::

  usage: lglass-regtool list-objects [-h] [--type TYPES]

  optional arguments:
    -h, --help            show this help message and exit
    --type TYPES, -T TYPES

Finding objects
---------------

To find a specific object without knowing its type there is the `find-objects`
subcommand. It takes a search term as first argument and returns the found
objects in the same format as `list-objects`.

::

  usage: lglass-regtool find-objects [-h] [--type TYPES] term               
   
  positional arguments:
    term

  optional arguments:
    -h, --help            show this help message and exit
    --type TYPES, -T TYPES

Finding inverse objects
-----------------------

To find inverse related objects for a given object there is the `find-inverse`
subcommand, which takes the type and the primary key of the base object and
returns a list of inverse related objects in the same format as `list-objects`.

::

  usage: lglass-regtool find-inverse [-h] type primary_key

  positional arguments:
    type
    primary_key

  optional arguments:
    -h, --help   show this help message and exit

Formatting objects
------------------

Objects are formatted by using the `format-object` subcommand. This subcommand
takes the type and the primary key of an object, reads the object, and writes
the reformatted version into the database.

::

  usage: lglass-regtool format-object [-h] type primary_key

  positional arguments:
    type
    primary_key

  optional arguments:
    -h, --help   show this help message and exit

Starting whois server
---------------------

To start a whoisd on the current database there is the `whoisd` subcommand,
which starts a whois server on port 4343 and host 127.0.0.1.

::

  usage: lglass-regtool whoisd [-h] [-4] [-6] [--host HOST] [--port PORT]
                               [--cidr] [--no-cidr] [--inverse] [--no-inverse]

  optional arguments:
    -h, --help            show this help message and exit
    -4                    Listen on IPv4
    -6                    Listen on IPv6
    --host HOST, -H HOST  Listen on host
    --port PORT, -p PORT  Listen on port
    --cidr, -c            Perform CIDR matching on queries
    --no-cidr             Do not perform CIDR matching on queries
    --inverse, -i         Perform inverse matching on queries
    --no-inverse          Do not perform inverse matching on queries

