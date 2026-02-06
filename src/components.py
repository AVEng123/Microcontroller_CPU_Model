from src.gates import ANDGate, ORGate, NOTGate, XORGate, NANDGate, NORGate

class HalfAdder:
    def __init__(self, label="HA"):
        self.label = label
        self.xor = XORGate(f"{label}_XOR")
        self.and_gate = ANDGate(f"{label}_AND")
        self.sum = 0
        self.carry = 0

    def execute(self, a, b):
        self.sum = self.xor.execute(a, b)
        self.carry = self.and_gate.execute(a, b)
        return self.sum, self.carry

    def __repr__(self):
        return f"HalfAdder({self.label}): sum={self.sum}, carry={self.carry}"

class FullAdder:
    def __init__(self, label="FA"):
        self.label = label
        self.ha1 = HalfAdder(f"{label}_HA1")
        self.ha2 = HalfAdder(f"{label}_HA2")
        self.or_gate = ORGate(f"{label}_OR")
        self.sum = 0
        self.carry_out = 0

    def execute(self, a, b, carry_in):
        s1, c1 = self.ha1.execute(a, b)
        self.sum, c2 = self.ha2.execute(s1, carry_in)
        self.carry_out = self.or_gate.execute(c1, c2)
        return self.sum, self.carry_out

    def __repr__(self):
        return f"FullAdder({self.label}): sum={self.sum}, carry_out={self.carry_out}"

class OneBitSubtractor:
    def __init__(self, label="SUB"):
        self.label = label
        self.full_adder = FullAdder(f"{label}_FA")
        self.not_b = NOTGate(f"{label}_NOT_B")
        self.difference = 0
        self.borrow_out = 0

    def execute(self, a, b, borrow_in):
        inverted_b = self.not_b.execute(b)
        self.difference, self.borrow_out = self.full_adder.execute(
            a, inverted_b, borrow_in
        )
        return self.difference, self.borrow_out

    def __repr__(self):
        return f"OneBitSubtractor({self.label}): diff={self.difference}, borrow={self.borrow_out}"

class SRLatch:
    def __init__(self, label="SR_LATCH"):
        self.label = label
        self.nor1 = NORGate(f"{label}_NOR1")
        self.nor2 = NORGate(f"{label}_NOR2")
        self.q = 0
        self.q_bar = 1

    def execute(self, set_input, reset_input):
        if set_input == 1 and reset_input == 1:
            pass
        elif set_input == 1:
            self.q = 1
            self.q_bar = 0
        elif reset_input == 1:
            self.q = 0
            self.q_bar = 1
        return self.q, self.q_bar

    def set(self):
        return self.execute(1, 0)

    def reset(self):
        return self.execute(0, 1)

    def hold(self):
        return self.execute(0, 0)

    def __repr__(self):
        return f"SRLatch({self.label}): Q={self.q}, Q_bar={self.q_bar}"

class Multiplexer2to1:
    def __init__(self, label="MUX_2to1"):
        self.label = label
        self.and1 = ANDGate(f"{label}_AND1")
        self.and2 = ANDGate(f"{label}_AND2")
        self.or_gate = ORGate(f"{label}_OR")
        self.not_gate = NOTGate(f"{label}_NOT")
        self.output = 0

    def execute(self, a, b, select):
        not_sel = self.not_gate.execute(select)
        term1 = self.and1.execute(a, not_sel)
        term2 = self.and2.execute(b, select)
        self.output = self.or_gate.execute(term1, term2)
        return self.output

    def __repr__(self):
        return f"Multiplexer2to1({self.label}): output={self.output}"

class DLatch:
    def __init__(self, label="D_LATCH"):
        self.label = label
        self.sr_latch = SRLatch(f"{label}_SR")
        self.not_gate = NOTGate(f"{label}_NOT")
        self.and1 = ANDGate(f"{label}_AND1")
        self.and2 = ANDGate(f"{label}_AND2")
        self.q = 0
        self.q_bar = 1

    def execute(self, data, enable):
        not_data = self.not_gate.execute(data)
        set_input = self.and1.execute(data, enable)
        reset_input = self.and2.execute(not_data, enable)
        self.q, self.q_bar = self.sr_latch.execute(set_input, reset_input)
        return self.q, self.q_bar

    def __repr__(self):
        return f"DLatch({self.label}): Q={self.q}, Q_bar={self.q_bar}"
