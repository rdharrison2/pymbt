"""
"""

from ast import *

SYMBOLS = {}
SYMBOLS[Add] = '+'
SYMBOLS[Sub] = '-'
SYMBOLS[Mult] = '*'
# NOTE: NuSMV is round towards zero, but Python truncate
#  - can use -old_div_op switch to get towards zero behaviour
SYMBOLS[Div] = '/'
SYMBOLS[Mod] = 'mod'
#SYMBOLS[Pow] = '**'
SYMBOLS[LShift] = '<<'
SYMBOLS[RShift] = '>>'
SYMBOLS[BitOr] = '|'
SYMBOLS[BitXor] = 'xor'
SYMBOLS[BitAnd] = '&'
#SYMBOLS[FloorDiv] = '//'
# BinOp
SYMBOLS[And] = '&'
SYMBOLS[Or] = '|'
# CmpOp
SYMBOLS[Eq] = '='
SYMBOLS[NotEq] = '!='
SYMBOLS[Lt] = '<'
SYMBOLS[LtE] = '<='
SYMBOLS[Gt] = '>'
SYMBOLS[GtE] = '>='
#SYMBOLS[Is] = 'is'
#SYMBOLS[IsNot] = 'is not'
#SYMBOLS[In] = 'in'
#SYMBOLS[NotIn] = 'not in'

SYMBOLS[Invert] = '!'
SYMBOLS[Not] = '!'
SYMBOLS[UAdd] = '+'
SYMBOLS[USub] = '-'

# NuSMV operator precedence, low to high
PREC = {}
PREC[IfExp] = 5
PREC[Or] = PREC[BitOr] = PREC[BitXor] = PREC[BitAnd] = 10
PREC[And] = 15
PREC[Eq] = PREC[NotEq] = PREC[Lt] = PREC[LtE] = PREC[Gt] = PREC[GtE] = 17
PREC[LShift] = PREC[RShift] = 18
PREC[Add] = PREC[Sub] = 20
PREC[Mult] = PREC[Div] = PREC[Mod] = 30
PREC[USub] = PREC[UAdd] = 40
PREC[Invert] = PREC[Not] = 45


def parse_expr(s):
    return parse(s, filename="<string>", mode="eval")

expr = parse_expr("x+1")
assignments = parse("x = 0; y=x+1; z=False", filename="<string>", mode="exec")


def to_nusmv(s):
    """Translates a Python expression to a NuSMV expression.
    """
    node = parse_expr(s)
    generator = NuSMVVisitor()
    generator.visit(node)
    return "".join(generator.result)


def expand_compare(node):
    """Expands "x < y <= z" to "x < y & y <= z"
    """
    nodes = []
    left = node.left
    for op, right in zip(node.ops, node.comparators):
        nodes.append(Compare(left, [op], [right]))
        left = right
    return BoolOp(And(), nodes)


class NuSMVException(Exception):
    pass


class NuSMVVisitor(NodeVisitor):
    """
    """

    def __init__(self):
        self.result = []

    def write(self, s):
        self.result.append(s)

    def _cannot_translate(self, node):
        raise NuSMVException("Cannot translate %r to a NuSMV expression" % dump(node))

    # atoms

    def visit_Name(self, node):
        if node.id in ('False', 'True'):
            self.write(node.id.upper())
        else:
            self.write(node.id)

    def visit_Num(self, node):
        if not isinstance(node.n, int):
            self._cannot_translate(node)
        self.write(repr(node.n))

    # expressions

    def get_op(self, node):
        if isinstance(node, (BinOp, BoolOp, UnaryOp)):
            return type(node.op)
        elif isinstance(node, Compare):
            # x > y > z gets converted to x > y & y > z
            return And if len(node.ops) > 1 else type(node.ops[0])
        elif isinstance(node, IfExp):
            return IfExp
        return None

    def get_op_precedence(self, node):
        op = self.get_op(node)
        if op and op in PREC:
            return PREC[op]
        return None

    def visit_operand(self, prec, node):
        prec2 = self.get_op_precedence(node)
        brackets = prec2 and prec2 < prec
        if brackets:
            self.write('(')
        self.visit(node)
        if brackets:
            self.write(')')

    def visit_Expression(self, node):
        self.visit(node.body)

    def visit_BinOp(self, node):
        prec = self.get_op_precedence(node)
        self.visit_operand(prec, node.left)
        self.write(' %s ' % SYMBOLS[type(node.op)])
        self.visit_operand(prec, node.right)

    def visit_BoolOp(self, node):
        prec = self.get_op_precedence(node)
        for idx, value in enumerate(node.values):
            if idx:
                self.write(' %s ' % SYMBOLS[type(node.op)])
            self.visit_operand(prec, value)

    def visit_Compare(self, node):
        if len(node.ops) > 1:
            node = expand_compare(node)
            print dump(node)
            self.visit(node)
        else:
            prec = self.get_op_precedence(node)
            self.visit_operand(prec, node.left)
            self.write(' %s ' % SYMBOLS[type(node.ops[0])])
            self.visit_operand(prec, node.comparators[0])

    def visit_UnaryOp(self, node):
        op = SYMBOLS[type(node.op)]
        if op != "+":
            # No unary add in NuSMV
            # FIXME: what does unary add do??
            self.write(op)
        self.visit_operand(self.get_op_precedence(node), node.operand)

    def visit_IfExp(self, node):
        prec = self.get_op_precedence(node)
        self.visit_operand(prec, node.test)
        self.write(' ? ')
        self.visit_operand(prec, node.body)
        self.write(' : ')
        self.visit_operand(prec, node.orelse)

    # FIXME: map useful built-ins
    # - abs(x) -> if x >= 0 then x else -x
    # - int, min/max 
    def visit_Call(self, node):
        want_comma = []
        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        self.visit(node.func)
        self.write('(')
        for arg in node.args:
            write_comma()
            self.visit(arg)
        for keyword in node.keywords:
            write_comma()
            self.write(keyword.arg + '=')
            self.visit(keyword.value)
        if node.starargs is not None:
            write_comma()
            self.write('*')
            self.visit(node.starargs)
        if node.kwargs is not None:
            write_comma()
            self.write('**')
            self.visit(node.kwargs)
        self.write(')')

    def generic_visit(self, node):
        self._cannot_translate(node)
