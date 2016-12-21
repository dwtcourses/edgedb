##
# Copyright (c) 2008-present MagicStack Inc.
# All rights reserved.
#
# See LICENSE for details.
##


from edgedb.server.pgsql import ast as pgast


class IRCompilerFunctionSupport:
    def visit_FunctionCall(self, expr):
        ctx = self.context.current

        result = None
        agg_filter = None
        agg_sort = []

        funcobj = expr.func

        if funcobj.aggregate:
            with self.context.new():
                ctx.in_aggregate = True
                ctx.query.aggregates = True
                args = [self.visit(a) for a in expr.args]
                if expr.agg_filter:
                    agg_filter = self.visit(expr.agg_filter)
        else:
            args = [self.visit(a) for a in expr.args]

        if expr.agg_sort:
            for sortexpr in expr.agg_sort:
                _sortexpr = self.visit(sortexpr.expr)
                agg_sort.append(
                    pgast.SortBy(
                        node=_sortexpr, dir=sortexpr.direction,
                        nulls=sortexpr.nones_order))

        partition = []
        if expr.partition:
            for partition_expr in expr.partition:
                _pexpr = self.visit(partition_expr)
                partition.append(_pexpr)

        if funcobj.from_function:
            funcname = funcobj.from_function
        else:
            raise NotImplementedError(
                f'unsupported function {funcobj.shortname}')

        name = (funcname,)

        if not result:
            if expr.window:
                window_sort = agg_sort
                agg_sort = None

            result = pgast.FuncCall(
                name=name, args=args,
                agg_order=agg_sort, agg_filter=agg_filter)

            if expr.window:
                result.over = pgast.WindowDef(
                    orderby=window_sort, partition=partition)

        return result
