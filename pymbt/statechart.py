"""Statechart 

Constructing the statechart from graphml:
 - 
 - 
 - validation
 - 
   - 
 
Using statecharts:

 - translation to NuSMV model to analyse
   - 
 - basic validation:
   - syntactic:
     - All 
   - syntactic, bit of semantic
 - simulation (borrow NuSMV ideas)
   - can we use IPython as the console?


     TODO
     
     
      coffee.fire()
     ... output describing step ...
     >>> sim
     Simulator([State('BUSY'), State('EMPTY')], {'m' : 0})
     >>> sim.
     >>> sim
     Simulator([State('BUSY'), State('EMPTY')], {'m' : 0})
     


    >>> sim.transitions[1].fire()
    ... ...
    >>> sim
    Simulator([State('IDLE'), State('NOTEMPTY')], {'m' : 0})
    
     
     
     - 
   - interaction:
     - user optionally picks initial state
     - 
   - calculate and offer expected inputs, and corresponding state transitions
   - choose one or more inputs
   - offer to step through microsteps to next step

 - test sequence generation (ala graphwalker)
   - A-Star
   - Random walk
   - 

"""

from yed_graphml import read_file
from transition import make_transition

import logging
log = logging.getLogger(__name__)


class StateError(Exception):
    pass


class State(object):
    """Base class for state chart states.
    """
    def __init__(self, label):
        self.label = label
        self.id = None
        self.parent = None
        self.states = []
        self.transitions = []

    def add_state(self, state):
        """Adds a child state to this state.
        """
        assert state.parent is None, "state has no parent"
        state.parent = self
        self.states.append(state)

    def add_transition(self, transition, destination):
        """Adds a transition from this state to the given destination state.
        """
        assert transition.source is None, "transition source is None"
        assert transition.destination is None, "transition destination is None"
        transition.source = self
        transition.destination = destination
        self.transitions.append(transition)

    def ancestors_to(self, other_state):
        """Returns an iterator of all ancestors of this state (including
        itself) up to but not including other_state.

        If other_state not found, raises StateError.
        """
        st = self
        while st != other_state:
            if st is None:
                raise StateError("Failed to find %r in %r ancestry" % (self, other_state))
            yield st
            st = st.parent

    def ancestors(self):
        """Returns an iterator of all ancestors of this state including
        itself.
        """
        return self.ancestors_to(None)

    def get_lca(self, other_state):
        """Returns the lowest common ancestor of this state and other_state,
        or raises StateError when no such ancestor exists.
        """
        my_ancestors = set(self.ancestors())
        for st in other_state.ancestors():
            if st in my_ancestors:
                return st
        raise StateError("No common ancestor found for %r and %r" % (self, other_state))

    def is_descendant(self, other_state, strict=False):
        """Is this state a descendant of other_state?

        :param strict: if True consider this state its own descendant (default: False)
        """
        st = self.parent if strict else self
        return st and other_state in st.ancestors()

    def is_ancestor(self, other_state, strict=False):
        """Is this state an ancestor of other_state?

        :param strict: if True consider this state its own ancestor (default: False)
        """
        return other_state.is_descendant(self, strict=strict)

    def is_basic(self):
        return not (self.is_or() or self.is_and())

    def is_or(self):
        return isinstance(self, StateChart)

    def is_and(self):
        return isinstance(self, AndState)

    def to_string(self, level=0):
        """Returns a simple presentation of the state hierarchy.

        >>> print state.to_string()
        StartChart('root')
        + AndState('ON')
          + StartChart('COFFEE')
            + State('BUSY')
            + State('IDLE')
          + StateChart('MONEY')
            + State('EMPTY')
            + State('NOTEMPTY')
        """
        prefix = "  " * (level - 1) + "+ " if level else ""
        s = [prefix + repr(self)]
        if self.states:
            for st in self.states:
                s.append(st.to_string(level=level + 1))
        return "\n".join(s)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.label)


class StateChart(State):
    """Statechart state.

    A statechart has a start (child) state and when active has
    exactly one active child state. It is also known as an OR-state.
    """
    def __init__(self, label):
        State.__init__(self, label)
        self.init = None
        self.start_state = None
        self.locals = None  # local variables

    def set_start_state(self, state):
        """Sets the start start.
        """
        assert state in self.states, "%r is a child state of %r" % (state, self)
        self.start_state = state

    def validate(self):
        """Validates the statechart.

        Constraints to check:
         * 
        """
        raise NotImplementedError


class AndState(State):
    """And state.
    """

    def get_orthogonal_states(self):
        """Returns all orthogonal substates, i.e. all descendants down
        to state-charts.
        """
        states = []
        for state in self.states:
            states.append(state)
            if state.is_and():
                states.extend(state.get_orthogonal_states())
        return states


class StateVisitor(object):
    """State visitor pattern.
    """

    def visit(self, state):
        """Visit a state."""
        method = 'visit_' + state.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(state)

    def generic_visit(self, state):
        """Called if no explicit visitor function exists for a state."""
        for state in self.states:
            self.visit(state)


def tree_walk(g, preorder=False, postorder=False):
    """Yields nodes of g depth-first in preorder and/or postorder.
    """
    from collections import deque
    seen = set()
    todo = deque(g.graph['children'])
    while todo:
        node = todo[0]
        if node in seen:
            todo.popleft()
            if postorder:
                yield node
        else:
            seen.add(node)
            if preorder:
                yield node
            if 'children' in g.node[node]:
                children = g.node[node]['children']
                todo.extendleft(children)


def make_statechart(g):
    """Creates a statechart from networkx graph.

    """
    def get_label(node_id):
        return g.node[node_id]['label']

    def is_start(node_id):
        return get_label(node_id).lower() == "start"
    root = StateChart(label=g.graph.get('name', 'root'))
    # node_id -> state
    states = dict()
    for node in tree_walk(g, postorder=True):
        data = g.node[node]
        log.debug("handling graph node %r (data=%r)", node, data)
        label = data['label']
        if 'children' in data:  # startchart/and-state
            start = None
            children = []
            for child_id in data['children']:
                st = states[child_id]
                if st.label.lower() == "start":
                    start = st
                    # TODO: complain about start nodes without exactly one successor!
                else:
                    children.append(st)
            if start:
                state = StateChart(label)
                start.parent = state
            else:
                state = AndState(label)
            for st in children:
                state.add_state(st)
        else:
            state = State(label)
        state.id = node
        states[node] = state
        if 'parent' not in data:
            if state.label.lower() == "start":
                state.parent = root
            else:
                root.add_state(state)

    # record inputs/outputs to determine locals later
    inputs = set()
    outputs = set()

    # handle transitions
    for (n1, n2, data) in g.edges(data=True):
        log.debug("handling graph edge %r -> %r (data=%r)", n1, n2, data)
        (src, dest) = (states[n1], states[n2])
        try:
            transition = make_transition(data.get('label', ''))
        except Exception as e:
            raise Exception("Failed to parse transition %r -> %r (data=%r): %s" % (src, dest, data, e))
        if src.label.lower() == "start":
            src.parent.set_start_state(dest)
            src.parent.init = transition
        else:
            # record inputs/outputs
            inputs.add(transition.event)
            outputs.update(transition.outputs)
            # add transition to src state
            src.add_transition(transition, dest)

    # local variables are intersection of inputs/outputs
    root.locals = inputs.intersection(outputs)
    return root


def read_statechart(filename):
    graphs = read_file(filename)
    g = graphs[0]
    return make_statechart(g)

if __name__ == "__main__":
    sc = read_statechart("../examples/cvm.graphml")
    print "statechart: ", sc.to_string()
