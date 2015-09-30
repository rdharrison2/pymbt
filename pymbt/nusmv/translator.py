"""NuSMV model translator.


"""


class NuSMVDef(object):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def to_string(self):
        return self.lhs + " := " + self.rhs + ";"


class NuSMVModel(object):

    def get_in_state(self):
        defs = []
        for state in self.states:
            label = state.label.lower()
            if state.parent:
                parent = state.parent.label.lower()
                nusmv_def = NuSMVDef(
                        "in-" + label,
                        "in-%s & %s=%s" % (parent, parent.upper(), label))
            else:
                nusmv_def = NuSMVDef("in-" + label, "TRUE")
            defs.append(nusmv_def)
        return defs

    def to_string(self):
        pass
