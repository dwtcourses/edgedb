import re
import hashlib
import base64

import postgresql
from postgresql.driver.dbapi20 import Cursor as CompatCursor

from semantix import caos

def quote_ident(text):
    """
    Quotes the identifier
    """
    result = postgresql.string.quote_ident(text)
    if result[0] != '"':
        return '"' + result + '"'
    return result

def qname(*parts):
    return '.'.join([quote_ident(q) for q in parts])


def pack_hstore(dct):
    if dct:
        result = []
        for key, value in dct.items():
            result.append(postgresql.string.quote_ident(key) + '=>'
                          + postgresql.string.quote_ident(str(value)))
        return ', '.join(result)
    else:
        return None


hstore_split_re = re.compile('("(?:[^"]|"")*")=>("(?:[^"]|"")*")')

def unpack_hstore(string):
    if not string:
        return None

    result = {}
    parts = hstore_split_re.split(string)[1:-1]
    count = (len(parts) + 1) // 3

    def _unquote(var):
        return var[1:-1].replace('""', '"')

    for i in range(0, count):
        key, value = parts[i*3:i*3+2]
        result[_unquote(key)] = _unquote(value)
    return result


def caos_name_to_pg_colname(name):
    if len(name) > 63:
        hash = base64.b64encode(hashlib.md5(name.encode()).digest()).decode().rstrip('=')
        name = hash + ':' + name[-(63 - 1 - len(hash)):]
    return name


class DatabaseObject(object):
    def __init__(self, connection):
        self.connection = connection
        self.cursor = CompatCursor(connection)

    def create(self):
        if self.create.__doc__ is None:
            raise Exception('missing DDL statement in docstring')

        try:
            self.runquery(self.create.__doc__)
        except postgresql.exceptions.DuplicateTableError:
            pass


class DatabaseTable(DatabaseObject):
    def insert(self, *dicts, **kwargs):
        data = {}
        for d in dicts + (kwargs,):
            data.update(d)

        if self.insert.__doc__ is None:
            raise Exception('missing insert statement in docstring')

        result = self.runquery(self.insert.__doc__, data)

        return result

    def runquery(self, query, params=None):
        query, pxf, nparams = self.cursor._convert_query(query)
        ps = self.connection.prepare(query)
        if params:
            return ps(*pxf(params))
        else:
            return ps()


class MetaObjectTable(DatabaseTable):
    def create(self):
        """
            CREATE TABLE "caos"."metaobject"(
                id serial NOT NULL,
                name text NOT NULL,
                title hstore,
                description hstore,

                PRIMARY KEY (id),
                UNIQUE (name)
            )
        """
        super().create()


class AtomTable(DatabaseTable):
    def create(self):
        """
            CREATE TABLE "caos"."atom"(
                automatic bool NOT NULL DEFAULT FALSE,

                PRIMARY KEY (id),
                UNIQUE (name)
            ) INHERITS ("caos"."metaobject")
        """
        super().create()

    def insert(self, *dicts, **kwargs):
        """
            INSERT INTO "caos"."atom"(id, name, title, description, automatic)
            VALUES (nextval('"caos"."metaobject_id_seq"'::regclass),
                    %(name)s, %(title)s::text::hstore, %(description)s::text::hstore, %(automatic)s)
            RETURNING id
        """
        kwargs['title'] = pack_hstore(kwargs['title'])
        kwargs['description'] = pack_hstore(kwargs['description'])
        return super().insert(*dicts, **kwargs)[0][0]


class ConceptTable(DatabaseTable):
    def create(self):
        """
            CREATE TABLE "caos"."concept"(
                PRIMARY KEY (id),
                UNIQUE (name)
            ) INHERITS ("caos"."metaobject")
        """
        super().create()

    def insert(self, *dicts, **kwargs):
        """
            INSERT INTO "caos"."concept"(id, name, title, description)
            VALUES (nextval('"caos"."metaobject_id_seq"'::regclass),
                    %(name)s, %(title)s::text::hstore, %(description)s::text::hstore)
            RETURNING id
        """
        kwargs['title'] = pack_hstore(kwargs['title'])
        kwargs['description'] = pack_hstore(kwargs['description'])
        return super().insert(*dicts, **kwargs)[0][0]


class LinkTable(DatabaseTable):
    def create(self):
        """
            CREATE TABLE "caos"."link"(
                source_id integer,
                target_id integer,
                mapping char(2) NOT NULL,
                required boolean NOT NULL DEFAULT FALSE,
                implicit boolean NOT NULL DEFAULT FALSE,
                atomic boolean NOT NULL DEFAULT FALSE,

                PRIMARY KEY (id)
            ) INHERITS("caos"."metaobject")
        """
        super().create()

    def insert(self, *dicts, **kwargs):
        """
            INSERT INTO "caos"."link"(id, source_id, target_id, name, mapping, required, title, description,
                                                                                         implicit, atomic)
                VALUES (
                            nextval('"caos"."metaobject_id_seq"'::regclass),
                            (SELECT id FROM caos.metaobject WHERE name = %(source)s),
                            (SELECT id FROM caos.metaobject WHERE name = %(target)s),
                            %(name)s,
                            %(mapping)s,
                            %(required)s,
                            %(title)s::text::hstore,
                            %(description)s::text::hstore,
                            %(implicit)s,
                            %(atomic)s
                ) RETURNING id
        """
        kwargs['title'] = pack_hstore(kwargs['title'])
        kwargs['description'] = pack_hstore(kwargs['description'])
        return super().insert(*dicts, **kwargs)[0][0]


class PathCacheTable(DatabaseTable):
    def create(self):
        """
            CREATE TABLE caos.path_cache (
                id uuid NOT NULL DEFAULT uuid_generate_v1mc(),

                entity_id           uuid NOT NULL,
                parent_entity_id    uuid,

                name_attribute      varchar(255),
                concept_name        varchar(255) NOT NULL,

                weight              integer,

                PRIMARY KEY (id),
                UNIQUE(entity_id, parent_entity_id)
            )
        """
        super().create()

    def insert(self, *dicts, **kwargs):
        """
            INSERT INTO
                caos.path_cache
                    (entity_id, parent_entity_id, name_attribute, concept_name, weight)

                VALUES(%(entity_id)s, %(parent_entity_id)s,
                       %(name_attribute)s, %(concept_name)s, %(weight)s)
            RETURNING entity_id
        """
        return super().insert(*dicts, **kwargs)
