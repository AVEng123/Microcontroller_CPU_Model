import math
from src.components import FullAdder, OneBitSubtractor, Multiplexer2to1
from src.gates import NOTGate, ANDGate, ORGate

class RippleCarryAdder8Bit:
    def __init__(self, label="RCA_8BIT"):
        self.label = label
        self.adders = [FullAdder(f"{label}_FA_{i}") for i in range(8)]
        self.result = [0] * 8
        self.carry_out = 0
        self.overflow = 0

    def execute(self, a_bits, b_bits):
        carry = 0
        for i in range(8):
            sum_bit, carry = self.adders[i].execute(a_bits[i], b_bits[i], carry)
            self.result[i] = sum_bit
        self.carry_out = carry
        a_sign = a_bits[7]
        b_sign = b_bits[7]
        result_sign = self.result[7]
        self.overflow = 1 if (a_sign == b_sign) and (result_sign != a_sign) else 0
        return self.result, self.carry_out, self.overflow

class TwosComplementSubtractor8Bit:
    def __init__(self, label="SUB_8BIT"):
        self.label = label
        self.adder = RippleCarryAdder8Bit(f"{label}_ADDER")
        self.inverters = [NOTGate(f"{label}_NOT_{i}") for i in range(8)]
        self.result = [0] * 8
        self.borrow_out = 0

    def execute(self, a_bits, b_bits):
        inverted_b = [self.inverters[i].execute(b_bits[i]) for i in range(8)]
        carry = 1
        result = []
        for i in range(8):
            sum_bit, carry = self.adder.adders[i].execute(a_bits[i], inverted_b[i], carry)
            result.append(sum_bit)
        self.result = result
        self.borrow_out = carry
        return self.result, self.borrow_out

class ShiftAndAddMultiplier8Bit:
    def __init__(self, label="MUL_8BIT"):
        self.label = label
        self.adders = [RippleCarryAdder8Bit(f"{label}_ADDER_{i}") for i in range(8)]
        self.product_low = [0] * 8
        self.product_high = [0] * 8

    def execute(self, a_bits, b_bits):
        product_high = [0] * 8
        product_low = [0] * 8
        for i in range(8):
            if b_bits[i] == 1:
                shifted_a = [0] * i + a_bits + [0] * (8 - i)
                low_part = shifted_a[:8] if len(shifted_a) >= 8 else shifted_a + [0] * (8 - len(shifted_a))
                product_low, carry, _ = self.adders[i].execute(product_low, low_part)
                if carry:
                    product_high = self._add_with_carry(product_high, [carry] + [0]*7)
        self.product_low = product_low
        self.product_high = product_high
        return self.product_low + self.product_high

    def _add_with_carry(self, a, b):
        result = []
        carry = 0
        for i in range(8):
            bit_sum = a[i] + b[i] + carry
            result.append(bit_sum % 2)
            carry = bit_sum // 2
        return result

class DividerBy8Bit:
    def __init__(self, label="DIV_8BIT"):
        self.label = label
        self.subtractor = TwosComplementSubtractor8Bit(f"{label}_SUB")
        self.quotient = [0] * 8
        self.remainder = [0] * 8
        self.division_by_zero = False

    def execute(self, dividend_bits, divisor_bits):
        if all(bit == 0 for bit in divisor_bits):
            self.division_by_zero = True
            return [0] * 8, dividend_bits, True
        self.division_by_zero = False
        quotient = 0
        remainder = self._bits_to_int(dividend_bits)
        divisor = self._bits_to_int(divisor_bits)
        while remainder >= divisor:
            remainder -= divisor
            quotient += 1
            if quotient > 255:
                break
        self.quotient = self._int_to_bits(quotient)
        self.remainder = self._int_to_bits(remainder)
        return self.quotient, self.remainder, self.division_by_zero

    @staticmethod
    def _bits_to_int(bits):
        result = 0
        for i, bit in enumerate(bits):
            result += bit * (2 ** i)
        return result

    @staticmethod
    def _int_to_bits(num, width=8):
        bits = []
        for i in range(width):
            bits.append((num >> i) & 1)
        return bits

class FloatingPointUnit8Bit:
    def __init__(self, label="FPU_8BIT"):
        self.label = label
        self.sign_bit = 0
        self.exponent = [0] * 3
        self.mantissa = [0] * 4
        self.value = 0.0
        self.is_zero = False
        self.is_infinity = False

    def parse(self, bits):
        if len(bits) != 8:
            raise ValueError("Input must be 8 bits")
        self.sign_bit = bits[7]
        self.exponent = bits[4:7]
        self.mantissa = bits[0:4]
        self._evaluate()
        return self.value

    def _evaluate(self):
        exp_val = sum(bit * (2 ** i) for i, bit in enumerate(self.exponent))
        mantissa_val = 1.0 + sum(bit * (2 ** (-i - 1)) for i, bit in enumerate(self.mantissa))
        if exp_val == 0:
            self.is_zero = True
            self.value = 0.0
        elif exp_val == 7:
            self.is_infinity = True
            self.value = float('inf')
        else:
            exp_unbiased = exp_val - 3
            self.value = ((-1) ** self.sign_bit) * mantissa_val * (2 ** exp_unbiased)
            self.is_zero = False
            self.is_infinity = False

    def create_from_float(self, value):
        if value == 0:
            self.bits = [0] * 8
            self.sign_bit = 0
            self.exponent = [0] * 3
            self.mantissa = [0] * 4
            self.is_zero = True
            return [0] * 8
        self.sign_bit = 1 if value < 0 else 0
        value = abs(value)
        exp = math.floor(math.log2(value))
        exp_biased = exp + 3
        if exp_biased >= 7:
            self.is_infinity = True
            exp_biased = 7
        elif exp_biased <= 0:
            exp_biased = 0
            self.is_zero = True
        self.exponent = [(exp_biased >> i) & 1 for i in range(3)]
        mantissa_val = (value / (2 ** exp)) - 1.0
        self.mantissa = []
        for i in range(4):
            bit_val = 2 ** (-i - 1)
            if mantissa_val >= bit_val:
                self.mantissa.append(1)
                mantissa_val -= bit_val
            else:
                self.mantissa.append(0)
        bits = self.mantissa + self.exponent + [self.sign_bit]
        return bits

    def add(self, fp1_bits, fp2_bits):
        val1 = self.parse(fp1_bits)
        val2 = self.parse(fp2_bits)
        result = val1 + val2
        return self.create_from_float(result)

    def multiply(self, fp1_bits, fp2_bits):
        val1 = self.parse(fp1_bits)
        val2 = self.parse(fp2_bits)
        result = val1 * val2
        return self.create_from_float(result)

class ALU8Bit:
    def __init__(self, label="ALU_8BIT"):
        self.label = label
        self.adder = RippleCarryAdder8Bit(f"{label}_ADDER")
        self.subtractor = TwosComplementSubtractor8Bit(f"{label}_SUB")
        self.multiplier = ShiftAndAddMultiplier8Bit(f"{label}_MUL")
        self.divider = DividerBy8Bit(f"{label}_DIV")
        self.fpu = FloatingPointUnit8Bit(f"{label}_FPU")
        self.result = [0] * 16
        self.flags = {'carry': 0, 'zero': 0, 'overflow': 0, 'sign': 0}

    def execute(self, a_bits, b_bits, operation):
        operation = operation & 0x7
        if operation == 0:
            self.result, carry, overflow = self.adder.execute(a_bits, b_bits)
            self.flags['carry'] = carry
            self.flags['overflow'] = overflow
        elif operation == 1:
            self.result, carry = self.subtractor.execute(a_bits, b_bits)
            self.flags['carry'] = carry
        elif operation == 2:
            self.result = self.multiplier.execute(a_bits, b_bits)
        elif operation == 3:
            quot, rem, div_zero = self.divider.execute(a_bits, b_bits)
            self.result = quot + rem
            self.flags['carry'] = 1 if div_zero else 0
        elif operation == 4:
            self.result = self.fpu.add(a_bits + [0] * 0, b_bits + [0] * 0)
        elif operation == 5:
            self.result = self.fpu.multiply(a_bits + [0] * 0, b_bits + [0] * 0)
        self.flags['zero'] = 1 if all(bit == 0 for bit in self.result[:8]) else 0
        self.flags['sign'] = self.result[7] if len(self.result) > 7 else 0
        return self.result, self.flags

class RegisterFile:
    def __init__(self, label="REG_FILE"):
        self.label = label
        self.registers = [0] * 8
        self.register_names = ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"]

    def read(self, reg_num):
        if 0 <= reg_num < 8:
            return self.registers[reg_num]
        return 0

    def write(self, reg_num, value):
        if 0 <= reg_num < 8:
            self.registers[reg_num] = value & 0xFF
            return True
        return False

    def get_all_registers(self):
        return {self.register_names[i]: self.registers[i] for i in range(8)}

    def reset(self):
        self.registers = [0] * 8

class Memory:
    def __init__(self, label="MEM", size=256):
        self.label = label
        self.size = size
        self.memory = [0] * size
        self.last_address = 0
        self.last_data = 0

    def read(self, address):
        if 0 <= address < self.size:
            self.last_address = address
            self.last_data = self.memory[address]
            return self.memory[address]
        return 0

    def write(self, address, value):
        if 0 <= address < self.size:
            self.memory[address] = value & 0xFF
            self.last_address = address
            self.last_data = value
            return True
        return False

    def get_memory_range(self, start_address, length=16):
        result = []
        for i in range(length):
            addr = (start_address + i) % self.size
            result.append({'address': addr, 'value': self.memory[addr]})
        return result

    def reset(self):
        self.memory = [0] * self.size

class ControlUnit:
    def __init__(self, label="CU"):
        self.label = label
        self.program_counter = 0
        self.instruction_register = 0
        self.operation = 0
        self.reg_src1 = 0
        self.reg_src2 = 0
        self.reg_dst = 0
        self.state = "FETCH"

    def decode_instruction(self, instruction):
        self.instruction_register = instruction
        self.operation = (instruction >> 6) & 0x3
        self.reg_dst = (instruction >> 4) & 0x3
        self.reg_src1 = (instruction >> 2) & 0x3
        self.reg_src2 = instruction & 0x3
        return {
            'operation': self.operation,
            'dst': self.reg_dst,
            'src1': self.reg_src1,
            'src2': self.reg_src2
        }

    def get_operation_name(self):
        ops = {0: "ADD", 1: "SUB", 2: "MUL", 3: "MOV"}
        return ops.get(self.operation, "UNKNOWN")

    def increment_pc(self):
        self.program_counter = (self.program_counter + 1) % 256

    def reset(self):
        self.program_counter = 0
        self.instruction_register = 0
        self.operation = 0
        self.state = "FETCH"

class DataBus:
    def __init__(self, label="DATA_BUS"):
        self.label = label
        self.data = 0
        self.source = "IDLE"
        self.destination = "IDLE"

    def transfer(self, source_name, data, destination_name):
        self.data = data & 0xFF
        self.source = source_name
        self.destination = destination_name
        return self.data

    def get_bits(self):
        bits = []
        for i in range(8):
            bits.append((self.data >> i) & 1)
        return bits

class AddressBus:
    def __init__(self, label="ADDR_BUS"):
        self.label = label
        self.address = 0
        self.source = "IDLE"

    def set_address(self, source_name, address):
        self.address = address & 0xFF
        self.source = source_name
        return self.address

    def get_bits(self):
        bits = []
        for i in range(8):
            bits.append((self.address >> i) & 1)
        return bits

class CPU8Bit:
    def __init__(self, label="CPU_8BIT"):
        self.label = label
        self.alu = ALU8Bit(f"{label}_ALU")
        self.registers = RegisterFile(f"{label}_REG_FILE")
        self.memory = Memory(f"{label}_MEM", size=256)
        self.control_unit = ControlUnit(f"{label}_CU")
        self.data_bus = DataBus(f"{label}_DATA_BUS")
        self.address_bus = AddressBus(f"{label}_ADDR_BUS")
        self.cycles = 0
        self.last_result = 0
        self.last_flags = {}
        self.last_reg_accessed = None
        self.alu_active = False
        self.last_memory_address = None
        self.last_memory_data = None

    def execute_instruction(self, instruction):
        info = {
            'instruction': instruction,
            'operation': '',
            'result': 0,
            'flags': {}
        }
        decoded = self.control_unit.decode_instruction(instruction)
        info['operation'] = self.control_unit.get_operation_name()
        operand_a_bits = self._int_to_bits(self.registers.read(decoded['src1']))
        operand_b_bits = self._int_to_bits(self.registers.read(decoded['src2']))
        operation = decoded['operation']
        result, flags = self.alu.execute(operand_a_bits, operand_b_bits, operation)
        result_value = self._bits_to_int(result)
        self.registers.write(decoded['dst'], result_value)
        self.data_bus.transfer(f"ALU", result_value, f"REG[R{decoded['dst']}]")
        self.last_result = result_value
        self.last_flags = flags
        self.cycles += 1
        self.control_unit.increment_pc()
        info['result'] = result_value
        info['flags'] = flags
        info['dst_register'] = decoded['dst']
        info['src1_register'] = decoded['src1']
        info['src2_register'] = decoded['src2']
        return result_value, flags, info

    def load_memory(self, address, value):
        self.memory.write(address, value)
        self.address_bus.set_address("CPU", address)
        self.data_bus.transfer("CPU", value, "MEMORY")

    def read_memory(self, address):
        self.address_bus.set_address("CPU", address)
        value = self.memory.read(address)
        self.data_bus.transfer("MEMORY", value, "CPU")
        return value

    def reset(self):
        self.registers.reset()
        self.memory.reset()
        self.control_unit.reset()
        self.cycles = 0
        self.last_result = 0
        self.last_flags = {}

    def get_cpu_state(self):
        return {
            'pc': self.control_unit.program_counter,
            'ir': self.control_unit.instruction_register,
            'registers': self.registers.get_all_registers(),
            'alu_result': self.last_result,
            'alu_flags': self.last_flags,
            'cycles': self.cycles,
            'data_bus': {'value': self.data_bus.data, 'source': self.data_bus.source, 'destination': self.data_bus.destination},
            'address_bus': {'address': self.address_bus.address, 'source': self.address_bus.source},
            'memory_view': self.memory.get_memory_range(self.control_unit.program_counter, 16)
        }

    @staticmethod
    def _int_to_bits(num, width=8):
        bits = []
        for i in range(width):
            bits.append((num >> i) & 1)
        return bits

    @staticmethod
    def _bits_to_int(bits):
        result = 0
        for i, bit in enumerate(bits):
            result += bit * (2 ** i)
        return result
