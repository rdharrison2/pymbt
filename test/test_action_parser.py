
import unittest

class TestActionParser(unittest.TestCase):
    labels = {
        "t1: power-on\n  / light-on;\n  m := 0" :
            ("t1", "power-on", None, ["light-on"], "m := 0"),
        "t2: power-off\n  / light-off" :
            ("t2", "power-off", None, ["light-off"], None),
        "coffee[m > 0] / start; dec" :
            (None, "coffee", "m > 0", ["start", "dec"], None),
        "inc [m<10] / m:=m+1" :
            (None, "inc", "m<0", [], "m:=m+1"),
        "inc / m:=1" :
            (None, "inc", None, [], "m:=1")
    }

