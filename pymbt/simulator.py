"""Statechart simulator

   repr(sim) shows current state[s] and variable values. When we
   create the simulator it needs to calculate initial variable values.

     >>> sim = statechart.get_simulator()
     >>> sim
     Simulator([State('OFF')], {'m' : 0})

   sim.transitions gives us external transitions that may
   occur in the current state (assuming their input is present).

     >>> sim.transitions
     [Transition('power-on / light-on; m = 0', State('On'))

   NOTE: THIS IS NOT IMPLEMENTED YET!!

   Transitions can either be enabled (their input added) or
   fired (input added and internal transitions fired until
   system acquiesces). When system acquiesces outputs are
   available as sim.outputs.

     >>> sim.transitions[0].fire()
     ... some output describing input and steps ...
     Simulator([State('IDLE'), State('NOTEMPTY')], {'m' : 0})
     >>> sim.outputs
     set('light-on')

    Only transitions whose guard is true will be displayed.
    Here 'coffee [m > 0] / start; dec' cannot occur as m=0.

     >>> sim.transitions
     [Transition('change / refund', State('IDLE')),
      Transition('inc [m < 10] / m = m + 1', State('NOTEMPTY')),
      Transition('power-off / light-off', State('OFF'))]

    Transitions can also be enabled if we want to fire more than
    one transition or explore the internal transitions of the step.

     >>> sim.transition[1].enable()
     >>> sim.transition[2].enable()
     >>> sim.enabled_inputs
     [Input('inc'), Input('power-off')]

    Enabled transitions are given by sim.enabled_transitions. Note
    that 'inc / [m < 10] / m = m + 1' is not actually enabled because
    it is superceded by 'power-off / light-off'.

     >>> sim.enabled_transitions
     [Transition('power-off / light-off', State('OFF'))]

    sim.step() simulates one small step of the state chart by
    firing enabled transitions to change state[s] and produce
    local/output events. When no 
    ,
    and sim.next() simulates a big step. sim.is_stable()
    tells us whether any transitions can fire. If the statechart
    encounters more than one enabled transition from a given
    state (i.e. non-determinism) it will by default raise an
    exception.

     >>> sim.next()
     ... some output describing the step ...
     Simulator([State('OFF')], {'m' : 1})
     >>> sim.is_stable()
     True
     >>> sim.outputs
     set('light-off')

    Can back-track the simulator using sim.back()

     >>> sim.back()
     ... output describing new state/transitions
     Simulator([State('IDLE'), State('NOTEMPTY')], {'m' : 0})

    Can also step statechart via inputs for possible transitions.
    If we use a custom class for the events we can support getattr()
    magic for tab completion in the shell.

     >>> sim.inputs
     EventSet(
      Input('change'),
      Input('inc'),
      Input('power-off'))
     >>> sim.inputs.inc.fire()
     ... output describing step ...
     Simulator([State('IDLE'), State('NOTEMPTY')], {'m' : 1})
     >>> sim.inputs.coffee.enable()
     >>> sim.inputs['inc'].enable()
     >>> sim.enabled_inputs
     EventSet(
      Input('coffee'),
      Input('inc'))
     >>> sim.step()
     ... output describing small step ...
     Simulator([State('BUSY'), State('NOTEMPTY')], {'m' : 2})
     >>> sim.is_stable()
     False
     >>> sim.outputs
     set('start')
     >>> sim.locals
     set('dec')
     >>> sim.transitions
     [Transition('power-off / light-off', State('OFF')),
"""

import logging
log = logging.getLogger(__name__)


class StateConfiguration(object):
    """Represents the current configuration of a statechart
    and the logic for transitioning between configurations.

    Note: in future this may also record historical information
    for history connectors.
    """
    def __init__(self, sc):
        # maps OR-state -> current_states
        self.active_states = dict()
        # cache of AND-state -> orthogonal_states
        self.and_states = dict()
        self._activate(sc.start_state)

    def get_active_states(self, only_basic=False):
        """Returns all the active states.
        """
        active_states = []
        for states in self.active_states.values():
            if only_basic:
                states = [st for st in states if st.is_basic()]
            active_states.extend(states)
        return active_states

    def get_active_transitions(self):
        """Returns transitions from all active states.
        """
        return [t for st in self.get_active_states() for t in st.transitions]

    def _deactivate(self, states):
        """Recursively deactivates a set of states.
        """
        for state in states:
            if state.is_or():
                new_states = self.active_states.pop(state)
                self._deactivate(new_states)

    def _get_orthogonal_states(self, and_state):
        """Returns all sub states including the state itself down to
        OR-states.
        """
        if and_state not in self.and_states:
            states = and_state.get_orthogonal_states()
            states.insert(0, and_state)
            self.and_states[and_state] = states
        return self.and_states[and_state]

    def _activate(self, state):
        """Recursively activates a state.
        """
        assert state.parent and state.parent.is_or(), \
            "%r.%r must be OR-state" % (state, state.parent)
        if state.is_and():
            states = self._get_orthogonal_states(state)
        else:  # OR/basic
            states = [state]
        # record the active state[s]
        self.active_states[state.parent] = states
        for state in states:
            if not state.is_or():
                continue
            # Note: state will often already be active when executing transition
            if state not in self.active_states:
                self._activate(state.start_state)

    def transition(self, transition):
        """Executes the given state transition.

        We deactivate (exit) all the active states in the transition scope OR-
        state (which must include the transition source state) then activate
        (enter) all the states from the transition destination up but not
        including the scope OR-state.
        """
        scope = transition.scope
        assert scope in self.active_states, \
                "transition scope %s must be active" % scope
        self._deactivate(self.active_states.pop(scope))

        # for each state in [destination..scope)
        for state in transition.destination.ancestors_to(scope):
            if not state.parent.is_or():
                continue
            self._activate(state)

    def __repr__(self):
        #states = ["%r=%r" % (k,v) for (k,v) in self.active_states.iteritems()]
        return "<%s active=%r>" % (self.__class__.__name__,
                self.get_active_states(only_basic=True))


class Input(object):
    """Represents a statechart input event.
    """
    def __init__(self, event, sim):
        self.sim = sim
        self.event = event

    def enable(self):
        self.sim.enabled_inputs.add(self.event)

    def fire(self):
        self.enable()
        self.sim.next()

    def __call__(self):
        return self.fire()

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __repr__(self):
        return "%s<%s>" % (self.__class__.__name__, self.event)


class EventSet(frozenset):
    """A set of events
    """

    def __getattr__(self, attr):
        for item in self:
            if item.event == attr:
                return item
        raise AttributeError

    def iterevents(self):
        return (item.event for item in self)

    def __dir__(self):
        return dir(self.__class__) + list(self.iterevents())


class Simulator(object):
    """Simulator for statecharts.
    """

    def __init__(self, statechart):
        self.sc = statechart
        self.states = StateConfiguration(statechart)
        self.variables = dict()
        self.enabled_inputs = set()
        self.outputs = set()
        self.locals = set()
        # list of (inputs,basic_states,variables,locals/outputs)
        self.trace = []
        self.log = log
        self.initialise()

    def initialise(self):
        """Initialises the simulator.

        Currently this just involves calculating the initial variables.
        """
        self.sc.init.exec_action(self.variables)

    def is_stable(self):
        """A statechart is stable when there are no inputs or enabled transitions.
        """
        return not(self.enabled_inputs or self.enabled_transitions)

    @property
    def active_states(self):
        """Returns the current active states.
        """
        return self.states.get_active_states()

    @property
    def transitions(self):
        """Returns possible transitions.
        """
        transitions = []
        for state in self.active_states:
            for transition in state.transitions:
                if transition.may_occur(self.variables):
                    transitions.append(transition)
        return transitions

    def _is_local(self, event):
        return self.sc.locals and event in self.sc.locals

    @property
    def inputs(self):
        """Returns expected input events in current states.
        """
        inputs = []
        for transition in self.transitions:
            if transition.event and not self._is_local(transition.event):
                inputs.append(Input(transition.event, self))
        return EventSet(inputs)

    def get_enabled_transitions_by_scope(self):
        """Calculates the possible transitions that by scope that
        are not overridden by high priority transitions.

        Note: transition.scope = lowest OR-state containing source
              and destination states
        """
        scopes = dict()
        # for all possible transitions...
        for transition in self.transitions:
            if transition.event and not (
                    transition.event in self.enabled_inputs or
                    transition.event in self.locals):
                continue
            my_scope = transition.scope
            for scope in scopes:
                if scope.is_ancestor(my_scope, strict=True):
                    # transition lower priority so ignore
                    break
                elif scope.is_descendant(my_scope, strict=True):
                    # transition higher priority
                    scopes.pop(scope)
            else:
                transitions = scopes.setdefault(my_scope, [])
                transitions.append(transition)
        return scopes

    @property
    def enabled_transitions(self):
        """Returns transitions that are enabled in the current states and not
        overridden by higher priority transitions.
        """
        transitions = []
        for trans in self.get_enabled_transitions_by_scope().values():
            transitions.extend(trans)
        return transitions

    def _execute_transition(self, transition, updates):
        self.log.info("Executing transition %r (scope=%r)", transition, transition.scope)
        # change state configuration
        self.states.transition(transition)
        self.log.info("State configuration is now %r", self.states)

        # add locals/outputs
        for event in transition.outputs:
            if self._is_local(event):
                self.locals.add(event)
            else:
                self.outputs.add(event)
        self.log.info("Local events now %r, outputs now %r", self.locals, self.outputs)

        # execute the action to update (a copy of) the variables
        variables = transition.exec_action(self.variables.copy())

        # collect variable updates
        for (var, val) in variables.items():
            if var not in self.variables:
                self.log.warn("Unknown variable %r in transition %r", var, transition)
                updates[var] = val
            elif self.variables[var] != val:
                if var in updates:
                    self.log.warn("Conflicting update of variable %r in transition %r", var, transition)
                updates[var] = val
        self.log.info("Variable updates = %r", updates)

    def step(self):
        """Performs a small step of the statechart.
        """
        self.log.info("Stepping %r", self)
        # get enabled transitions before reseting inputs
        scope_transitions = self.get_enabled_transitions_by_scope()

        # reset inputs/outputs at the start of a big step
        if self.enabled_inputs:
            self.log.info("Reseting inputs and outputs at start of big step...")
            self.enabled_inputs = set()
            self.outputs = set()
        self.locals = set()

        # execute transitions
        # - note that each scope is non-overlapping by definition
        updates = dict()
        for scope, transitions in scope_transitions.items():
            if len(transitions) > 1:  # non-determinism
                pass
            transition = transitions[0]
            self._execute_transition(transition, updates)

        # update variables
        self.variables.update(updates)
        self.log.info("Variables now %r", self.variables)

    def next(self):
        """Performs a big step of the statechart.
        """
        while not self.is_stable():
            self.step()

    def back(self, steps=1):
        """Backtracks the given number of big steps.
        """
        raise NotImplementedError

    def __repr__(self):
        return "<%s states=%r,variables=%r>" % (
                self.__class__.__name__,
                self.states,
                self.variables)


def read_simulator(filename):
    from statechart import read_statechart
    sc = read_statechart(filename)
    print "statechart: ", sc.to_string()
    sim = Simulator(sc)
    return sim

if __name__ == "__main__":
    logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s: [%(name)s]: %(levelname)s: %(message)s")
    import os
    dirname = os.path.dirname(__file__)
    sim = read_simulator(os.path.join(dirname, "../examples/duo_stealing_plus.graphml"))
