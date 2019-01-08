#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2018-present MagicStack Inc. and the EdgeDB authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from edb.eschema.pygments import EdgeSchemaLexer

from sphinx import domains as s_domains
from sphinx.directives import code as s_code

from . import shared


class EschemaSynopsisDirective(s_code.CodeBlock):

    has_content = True
    optional_arguments = 0
    required_arguments = 0
    option_spec = {}

    def run(self):
        self.arguments = ['eschema-synopsis']
        return super().run()


class EschemaDomain(s_domains.Domain):

    name = "eschema"
    label = "EdgeDB Schema"

    directives = {
        'synopsis': EschemaSynopsisDirective,
    }


def setup_domain(app):
    app.add_lexer("eschema", EdgeSchemaLexer())
    app.add_lexer("eschema-synopsis", EdgeSchemaLexer())

    app.add_role(
        'eschema:synopsis',
        shared.InlineCodeRole('eschema-synopsis'))

    app.add_domain(EschemaDomain)