class LogicGate:
    def __init__(self, label):
        self.label = label
        self.output = 0

    def __repr__(self):
        return f"{self.__class__.__name__}({self.label})"

class ANDGate(LogicGate):
    def execute(self, a, b):
        self.output = 1 if (a == 1 and b == 1) else 0
        return self.output

class ORGate(LogicGate):
    def execute(self, a, b):
        self.output = 1 if (a == 1 or b == 1) else 0
        return self.output

class NOTGate(LogicGate):
    def execute(self, a):
        self.output = 1 if a == 0 else 0
        return self.output

class XORGate(LogicGate):
    def execute(self, a, b):
        self.output = 1 if a != b else 0
        return self.output

class NANDGate(LogicGate):
    def execute(self, a, b):
        self.output = 0 if (a == 1 and b == 1) else 1
        return self.output

class NORGate(LogicGate):
    def execute(self, a, b):
        self.output = 1 if (a == 0 and b == 0) else 0
        return self.output
