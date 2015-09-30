"""Statechart transitions.
"""

import ast
import re

import logging
log = logging.getLogger("transition")

# <name>:<event>[<guard>]/<output>[;<output>]*;<actions>
# e.g. t1: power_on [m>0] / lights_on ;  m=m+1
re_label = re.compile(r"""
    ((?P<name>\w+)\s*:)?\s*
    (?P<event>\w+)?\s*
    (\[\s*(?P<guard>[^]]+)\s*\])?\s*
    (/\s*(?P<output_actions>.*))?\s*$
""", re.M | re.VERBOSE)


class ParseError(Exception):
    pass


class Transition(object):
    """Represents a statechart transition.
    """

    # source, destination, and scope states
    source = None
    destination = None
    _scope = None

    def __init__(self, event, guard=None, outputs=None, action=None, name=None):
        self.event = event
        self.outputs = outputs or []
        self.name = name
        self.defines = []
        self.guard_s = guard
        self.action_s = action
        # Note: guard and action may be ASTs
        if guard:
            try:
                self.guard_ast = ast.parse(guard, "<string>", mode="eval")
                self.guard = compile(self.guard_ast, "<string>", mode="eval")
            except SyntaxError as e:
                raise ParseError("Failed to parse guard %r (column=%s)" % (guard, e.offset))
        else:
            (self.guard_ast, self.guard) = (None, None)
        if action:
            try:
                self.action_ast = ast.parse(action, "<string>", mode="exec")
                self.action = compile(self.action_ast, "<string>", mode="exec")
            except SyntaxError as e:
                raise ParseError("Failed to parse action %r (column=%s)" % (action, e.offset))
        else:
            (self.action_ast, self.action) = (None, None)

    def _analyse_action_ast(self):
        # this should split the action into separate assignments
        pass

    def get_assignments(self):
        """Returns assignments as [(name,ast_value)]
        """
        if not self.action:
            return []

    def eval_guard(self, variables):
        if self.guard:
            return eval(self.guard, globals(), variables)
        else:
            return True
    may_occur = eval_guard

    def exec_action(self, variables):
        if self.action:
            # TODO: multiple assignments should be independent
            #  exec_action("x=4; y=x+1",dict(x=1,y=1)) means y=2 not 5
            exec(self.action, globals(), variables)
        return variables

    @property
    def scope(self):
        """Returns the 'scope' of the transition, being the lowest
        common ancestor OR-state of both source and destination states.
        """
        if self._scope is None:
            if self.source is None:
                raise TypeError("%r has no source state yet" % self)
            if self.destination is None:
                raise TypeError("%r has no destination state yet" % self)
            lca = self.source.get_lca(self.destination)
            while lca and not lca.is_or():
                lca = lca.parent
            assert lca is not None, "Failed to find scope of (%r,%r)" % (
                    self.source, self.destination)
            self._scope = lca
        return self._scope

    def get_label(self):
        """Returns the string representation of the transition.

        For example, "t1: power_on [m>0] / lights_on ;  m=m+1"
        """
        parts = []
        if self.name:
            parts.append(self.name + " :")
        if self.event:
            parts.append(self.event)
        if self.guard_s:
            parts.append("[" + self.guard_s + "]")
        if self.outputs or self.action_s:
            actions = list(self.outputs)
            if self.action:
                actions.append(self.action_s)
            parts.append("/ " + "; ".join(actions))
        return " ".join(parts)

    def __repr__(self):
        return "%s%r" % (self.__class__.__name__,
                (self.get_label(), self.destination))


def make_transition(label):
    """Parses a transition label of the form:

    [<name> :] <event> [[<guard>]] [/ [<outputs>] ; [<action>] ]

    e.g. t1: power_on [m>0] / lights_on ;  m=m+1
    """
    m = re_label.match(label)
    if m is None:
        raise ParseError("Could not regex label %r (pattern=%s)" % (label, re_label.pattern))
    name = m.group('name')
    event = m.group('event')
    guard = m.group('guard')
    output_actions = m.group('output_actions') or ""
    stmts = re.split("\s*;\s*", output_actions.strip())
    outputs = []
    re_word = re.compile("^\w+$")
    while stmts and re_word.match(stmts[0]):
        outputs.append(stmts.pop())
    action = "; ".join(stmts)
    return Transition(event, guard=guard, outputs=outputs, action=action, name=name)

if __name__ == "__main__":
    label = "t1: power_on [m>0] / lights_on ;  m=m+1"
    transition = make_transition(label)
    print "transition: ", repr(transition)

