Objects
=======

The lglass registry objects are simple key-value pairs which hold the complete
registry information. Therefore you can imagine it as a schema-less database
like MongoDB, but without the introduced bloat. Instead lglass object keys and
values are always strings and the format is well-defined but also compatible
to other registries.

The first key-value pair of an object defines the type resp. the primary key of
the object. All subsequent key-value pairs are not enforced by the registry
structure, but can also hold information like primary keys, inverse keys and
other values.

In fact, you should follow RFC2622 about RPSL if you want to use lglass objects
for your Internet registry because it defines a feature-complete routing policy
language which is parsable for several software plattforms. At the moment,
lglass lacks such a parser.

Any key or value can hold an UTF-8 string.

Serialisation
-------------

The serialisation of objects is oriented on RFC2622 and the RIPE NCC registry
output. Each key-value pair is printed on one line, and the key and value are
separated by a colon. If the value has multiple lines the next line will begin
with a whitespace character.

::

  aut-num:        AS76198
  org:            NERDISTAN-DN42
  as-name:        EMBASSY-AS
  descr:          Embassy of Nerdistan AS
  admin-c:        DEELKAR-DN42
  tech-c:         DEELKAR-DN42
  tech-c:         CREST-DN42
  tech-c:         PYROPETER-DN42

Inverse relations
-----------------

The lglass object model supports inverse relations, which mean that a field
value can hold the primary key of another object and your software can resolve
that relation automatically by using the schema information.

In the above example, the field ``admin-c`` would be an inverse field and
contain the primary key of any desirable person object. Therefore, the given
object refers to the person object with primary key ``DEELKAR-DN42``.

Schemas
-------

lglass also provides a simple schema description language on top of the object
format. Schema objects consists of the ``type-name`` key which defines the name
of the type covered by the schema and many ``key`` keys which contain a simple
pseudo language.

::

  schema:          AUT-NUM-SCHEMA
  type-name:       aut-num
  key:             aut-num mandatory single primary lookup
  key:             as-name mandatory single
  key:             descr optional multiple
  key:             member-of optional multiple inverse as-set
  key:             import optional multiple
  key:             mp-import optional multiple
  key:             export optional multiple
  key:             mp-export optional multiple
  key:             default optional multiple
  key:             mp-default optional multiple
  key:             remarks optional multiple
  key:             admin-c optional multiple inverse person
  key:             tech-c optional multiple inverse person
  key:             org optional multiple inverse organisation
  key:             mnt-by optional multiple inverse mntner

This approach leads to a schema-object-describing schema:

::

  schema:          SCHEMA-SCHEMA
  type-name:       schema
  key:             schema mandatory single primary lookup
  key:             type-name mandatory single lookup
  key:             key mandatory multiple

Each ``key`` value has the same format: ``{keyname} {tags}+``, where tags is one
of ``mandatory``, ``optional``, ``multiple``, ``single``, ``primary``, ``lookup``.
Furthermore you can specify the special inverse tag which has a value containing
a comma-separated list of type names.


