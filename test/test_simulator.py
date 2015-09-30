
import unittest

from pymbt import simulator
from pymbt.statechart import StateChart


class SimulatorTestCase(unittest.TestCase):

    def create_cvm_statechart(self):
        sc = StateChart("CVM")
        
    def setUp(self):
        self.sc = self.create_cvm_statechart()
        self.sim = self.sc.get_simulator()

    def test_repr(self):
        self.assertEqual("Simulator([State('OFF')], {'m' : 0})", repr(self.sim))

