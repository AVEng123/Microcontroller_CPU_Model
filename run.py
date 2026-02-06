
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import sys
from pathlib import Path
import re
import subprocess
import tempfile
import os
import time
import threading

sys.path.insert(0, str(Path(__file__).parent))

from src.cpu import CPU8Bit

class CCompiler:
    """Simple C to CPU instruction compiler"""

    def __init__(self):
        self.variables = {}
        self.memory_ptr = 0x00
        self.instructions = []
        self.error_log = []

    def compile(self, c_code):
        """Compile C code to CPU instructions"""
        self.variables = {}
        self.memory_ptr = 0x00
        self.instructions = []
        self.error_log = []

        lines = c_code.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue

            try:
                if '=' in line and not line.startswith('if'):
                    self._compile_assignment(line)
                elif line.startswith('if'):
                    self._compile_if(line)
                elif line.startswith('for') or line.startswith('while'):
                    self._compile_loop(line)
            except Exception as e:
                self.error_log.append(f"Error: {str(e)}")

        return self.instructions, self.variables, self.error_log

    def _compile_assignment(self, line):
        """Compile variable assignment: x = 5 or x = y + z"""
        line = line.rstrip(';')
        match = re.match(r'(int\s+)?(\w+)\s*=\s*(.+)', line)
        if not match:
            raise ValueError(f"Invalid assignment: {line}")

        is_declaration = match.group(1) is not None
        var_name = match.group(2)
        expression = match.group(3).strip()

        if is_declaration or var_name not in self.variables:
            self.variables[var_name] = self.memory_ptr
            self.memory_ptr += 1

        if expression.isdigit():
            value = int(expression)
            instr = self._create_load_instruction(var_name, value)
            self.instructions.append(instr)

        elif '+' in expression:
            parts = expression.split('+')
            left = parts[0].strip()
            right = parts[1].strip()
            self.instructions.append({
                'op': 'ADD',
                'dst': var_name,
                'src1': left,
                'src2': right
            })

        elif '-' in expression:
            parts = expression.split('-')
            left = parts[0].strip()
            right = parts[1].strip()
            self.instructions.append({
                'op': 'SUB',
                'dst': var_name,
                'src1': left,
                'src2': right
            })

        elif '*' in expression:
            parts = expression.split('*')
            left = parts[0].strip()
            right = parts[1].strip()
            self.instructions.append({
                'op': 'MUL',
                'dst': var_name,
                'src1': left,
                'src2': right
            })

        else:
            self.instructions.append({
                'op': 'MOV',
                'dst': var_name,
                'src1': expression,
                'src2': '0'
            })

    def _compile_if(self, line):
        """Compile if statements (basic)"""
        self.instructions.append({
            'op': 'IF',
            'condition': line
        })

    def _compile_loop(self, line):
        """Compile loops (basic)"""
        self.instructions.append({
            'op': 'LOOP',
            'condition': line
        })

    def _create_load_instruction(self, var_name, value):
        """Create a load/move instruction"""
        return {
            'op': 'LOAD',
            'dst': var_name,
            'value': value
        }

class BitDisplay(tk.Canvas):
    def __init__(self, parent, bit_value=0, size=25, **kwargs):
        super().__init__(parent, width=size, height=size, **kwargs)
        self.bit_value = bit_value
        self.size = size
        self.update_display()

    def set_bit(self, value):
        self.bit_value = value
        self.update_display()

    def update_display(self):
        self.delete("all")
        color = "red" if self.bit_value == 1 else "blue"
        margin = 2
        self.create_oval(margin, margin, self.size-margin, self.size-margin,
                        fill=color, outline="black", width=2)
        self.create_text(self.size//2, self.size//2, text=str(self.bit_value),
                        font=("Arial", 8, "bold"), fill="white")

class BusVisualizer(tk.Frame):
    def __init__(self, parent, bus_name="Bus", bits=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.bus_name = bus_name
        self.bits = bits if bits else [0]*8

        label = tk.Label(self, text=bus_name, font=("Arial", 9, "bold"), bg="lightgray")
        label.pack(side=tk.TOP, fill=tk.X)

        bits_frame = tk.Frame(self, bg="white")
        bits_frame.pack(side=tk.TOP, fill=tk.X, padx=3, pady=3)

        self.bit_displays = []
        for i in range(8):
            bd = BitDisplay(bits_frame, bit_value=self.bits[i], size=20)
            bd.pack(side=tk.LEFT, padx=1)
            self.bit_displays.append(bd)

        self.value_label = tk.Label(self, text="0x00", font=("Arial", 10, "bold"), bg="lightyellow")
        self.value_label.pack(side=tk.TOP, fill=tk.X, padx=3, pady=3)

    def update_bus(self, bits):
        self.bits = bits
        for i, bd in enumerate(self.bit_displays):
            if i < len(bits):
                bd.set_bit(bits[i])
        value = sum(bits[i] * (2**i) for i in range(8))
        self.value_label.config(text=f"0x{value:02X} ({value})")

class CPUVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("CPU Simulator with C Program Execution")
        self.root.geometry("1600x1000")
        self.root.config(bg="white")

        self.cpu = CPU8Bit()
        self.compiler = CCompiler()
        self.execution_thread = None
        self.is_running = False
        self.execution_speed = 500

        self.c_program_memory = {}
        self.c_variables = {}
        self.memory_allocations = []

        self.current_gate_states = {}
        self.current_alu_bits = {'a': [0]*8, 'b': [0]*8, 'result': [0]*8}
        self.clock_phase = 0
        self.current_micro_op = ""
        self.data_flow_log = []
        self.pointer_map = {}
        self.heap_start = 0x40
        self.heap_ptr = self.heap_start

        self.gpio_state = {'LED': 0, 'BUTTON': 0}
        self.timer_state = {'ms': 0, 'enabled': False}
        self.isr_state = {'active': False, 'name': ''}
        self.watchdog_state = {'enabled': False, 'counter': 0}
        self.debounce_state = {'raw': 0, 'stable': 0, 'count': 0}

        self.create_unified_layout()
        self.update_displays()

    def create_unified_layout(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_panel = ttk.Frame(main_paned)
        main_paned.add(left_panel, weight=1)

        self.create_code_editor(left_panel)

        right_panel = ttk.Frame(main_paned)
        main_paned.add(right_panel, weight=2)

        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        main_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text="CPU State")
        self.create_cpu_visualization(main_tab)

        gates_tab = ttk.Frame(self.notebook)
        self.notebook.add(gates_tab, text="Gates & Logic")
        self.create_gates_visualization(gates_tab)

        alu_tab = ttk.Frame(self.notebook)
        self.notebook.add(alu_tab, text="ALU & Control")
        self.create_alu_control_visualization(alu_tab)

        clock_tab = ttk.Frame(self.notebook)
        self.notebook.add(clock_tab, text="Clock & Timing")
        self.create_clock_visualization(clock_tab)

    def create_code_editor(self, parent):
        """C code editor with execution controls"""
        frame = ttk.LabelFrame(parent, text="C Program", padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(btn_frame, text="🔨 Compile & Execute",
                  command=self.compile_and_execute).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="⏸ Pause",
                  command=self.pause_execution).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Reset",
                  command=self.reset_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 Load",
                  command=self.load_c_file).pack(side=tk.LEFT, padx=5)

        editor_frame = ttk.Frame(frame)
        editor_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))

        scroll = ttk.Scrollbar(editor_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.code_editor = tk.Text(editor_frame, height=12, width=50,
                                   yscrollcommand=scroll.set, font=("Courier", 9))
        self.code_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.code_editor.yview)

        sample_code = '''

int main() {
    int arrayA[5] = {10, 20, 30, 40, 50};
    int arrayB[5] = {5, 15, 25, 35, 45};
    int result[5];

    for(int i = 0; i < 5; i++) {
        result[i] = arrayA[i] + arrayB[i];
    }
    return 0;
}'''
        self.code_editor.insert("1.0", sample_code)

        status_frame = ttk.LabelFrame(frame, text="Execution Status & Output", padding="5")
        status_frame.pack(fill=tk.BOTH, expand=True)

        self.status_text = tk.Text(status_frame, height=20, width=50,
                                   font=("Courier", 8), bg="lightyellow")
        self.status_text.pack(fill=tk.BOTH, expand=True)

    def create_cpu_visualization(self, parent):
        """Real-time CPU visualization with enhanced hardware activity"""
        main_viz = ttk.Frame(parent)
        main_viz.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.LabelFrame(main_viz, text="🔴 CPU REGISTERS (8-bit)", padding="10", relief=tk.RIDGE)
        top_frame.pack(fill=tk.X, pady=(0, 5), padx=5)

        self.reg_displays = {}
        for i in range(8):
            r_frame = ttk.Frame(top_frame)
            r_frame.pack(fill=tk.X, padx=10, pady=3)

            reg_name = f"R{i} (SP)" if i == 7 else f"R{i}"
            ttk.Label(r_frame, text=f"{reg_name}:", width=10, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

            label = tk.Label(r_frame, text="0x00 (0)", font=("Courier", 10, "bold"),
                           bg="lightblue", width=20, padx=5, relief=tk.SUNKEN, bd=2)
            label.pack(side=tk.LEFT, padx=5)
            self.reg_displays[i] = label

        bus_frame = ttk.LabelFrame(main_viz, text="🔌 BUS ACTIVITY", padding="10", relief=tk.RIDGE)
        bus_frame.pack(fill=tk.X, pady=(0, 5), padx=5)

        data_bus_frame = ttk.Frame(bus_frame)
        data_bus_frame.pack(fill=tk.X, pady=5)
        ttk.Label(data_bus_frame, text="📤 Data Bus:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.databus_label = tk.Label(data_bus_frame, text="[IDLE] Value: 0x00 | Source: - | Dest: -",
                                      font=("Courier", 10, "bold"), bg="#FFFF99", padx=10, pady=5,
                                      relief=tk.SUNKEN, bd=2, width=60, anchor="w")
        self.databus_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        addr_bus_frame = ttk.Frame(bus_frame)
        addr_bus_frame.pack(fill=tk.X, pady=5)
        ttk.Label(addr_bus_frame, text="📍 Addr Bus:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.addrbus_label = tk.Label(addr_bus_frame, text="[IDLE] Address: 0x00 | Source: -",
                                      font=("Courier", 10, "bold"), bg="#FFFF99", padx=10, pady=5,
                                      relief=tk.SUNKEN, bd=2, width=60, anchor="w")
        self.addrbus_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        middle_frame = ttk.LabelFrame(main_viz, text="⚙️  CONTROL UNIT & ALU", padding="10", relief=tk.RIDGE)
        middle_frame.pack(fill=tk.X, pady=(0, 5), padx=5)

        cu_frame = ttk.Frame(middle_frame)
        cu_frame.pack(fill=tk.X, pady=5)

        ttk.Label(cu_frame, text="🔄 PC:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.pc_label = tk.Label(cu_frame, text="0x00", font=("Courier", 10, "bold"),
                                bg="#CCFFCC", width=5, relief=tk.SUNKEN, bd=2)
        self.pc_label.pack(side=tk.LEFT, padx=3)

        ttk.Label(cu_frame, text="| 📋 IR:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.ir_label = tk.Label(cu_frame, text="0x00", font=("Courier", 10, "bold"),
                                bg="#CCFFCC", width=5, relief=tk.SUNKEN, bd=2)
        self.ir_label.pack(side=tk.LEFT, padx=3)

        ttk.Label(cu_frame, text="| ⏱️  Cycles:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.cycles_label = tk.Label(cu_frame, text="0", font=("Courier", 10, "bold"),
                                     bg="#CCFFCC", width=5, relief=tk.SUNKEN, bd=2)
        self.cycles_label.pack(side=tk.LEFT, padx=3)

        alu_frame = ttk.Frame(middle_frame)
        alu_frame.pack(fill=tk.X, pady=5)

        ttk.Label(alu_frame, text="🧮 ALU Result:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.alu_result_label = tk.Label(alu_frame, text="0x00", font=("Courier", 10, "bold"),
                                        bg="#FFCCCC", width=5, relief=tk.SUNKEN, bd=2)
        self.alu_result_label.pack(side=tk.LEFT, padx=3)

        ttk.Label(alu_frame, text="| 🚩 Flags [C:Z:O:S]:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.flags_label = tk.Label(alu_frame, text="[0:0:0:0]", font=("Courier", 10, "bold"),
                                   bg="#FFCCCC", width=10, relief=tk.SUNKEN, bd=2)
        self.flags_label.pack(side=tk.LEFT, padx=3)

        bottom_frame = ttk.LabelFrame(main_viz, text="💾 Memory & Stack", padding="10", relief=tk.RIDGE)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        mem_scroll = ttk.Scrollbar(bottom_frame)
        mem_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.memory_display = tk.Text(bottom_frame, height=8, width=80,
                                      yscrollcommand=mem_scroll.set,
                                      font=("Courier", 9), bg="white")
        self.memory_display.pack(fill=tk.BOTH, expand=True)
        mem_scroll.config(command=self.memory_display.yview)

        self.memory_display.tag_config("data_region", background="lightyellow", relief=tk.FLAT)
        self.memory_display.tag_config("stack_region", background="lightgreen", relief=tk.FLAT)
        self.memory_display.tag_config("sp_pointer", background="salmon", font=("Courier", 9, "bold"))
        self.memory_display.tag_config("active_address", background="gold", font=("Courier", 9, "bold"))

    def create_gates_visualization(self, parent):
        """Create live gates visualization with animated gate operations"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=5)

        ttk.Label(header_frame, text="🔌 Live Logic Gates & Digital Logic Flow",
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        self.gate_status_label = tk.Label(header_frame, text="⚪ IDLE",
                                          font=("Courier", 10, "bold"), bg="lightgray", padx=10)
        self.gate_status_label.pack(side=tk.RIGHT, padx=10)

        gate_canvas_frame = ttk.LabelFrame(main_frame, text="🎯 Live Full Adder Operation (8-bit Ripple Carry)", padding=10)
        gate_canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.gates_canvas = tk.Canvas(gate_canvas_frame, bg="#1a1a2e", height=200, relief=tk.SUNKEN, bd=2)
        self.gates_canvas.pack(fill=tk.BOTH, expand=True)

        bits_frame = ttk.LabelFrame(main_frame, text="📊 Bit-Level Data Flow", padding=10)
        bits_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        a_frame = ttk.Frame(bits_frame)
        a_frame.pack(fill=tk.X, pady=3)
        ttk.Label(a_frame, text="Input A:  ", font=("Courier", 10, "bold")).pack(side=tk.LEFT)
        self.bit_labels_a = []
        for i in range(7, -1, -1):
            lbl = tk.Label(a_frame, text="0", font=("Courier", 12, "bold"),
                          bg="#333", fg="#0f0", width=3, relief=tk.RIDGE)
            lbl.pack(side=tk.LEFT, padx=2)
            self.bit_labels_a.append(lbl)
        self.value_label_a = tk.Label(a_frame, text="= 0x00 (0)", font=("Courier", 10), bg="white")
        self.value_label_a.pack(side=tk.LEFT, padx=10)

        b_frame = ttk.Frame(bits_frame)
        b_frame.pack(fill=tk.X, pady=3)
        ttk.Label(b_frame, text="Input B:  ", font=("Courier", 10, "bold")).pack(side=tk.LEFT)
        self.bit_labels_b = []
        for i in range(7, -1, -1):
            lbl = tk.Label(b_frame, text="0", font=("Courier", 12, "bold"),
                          bg="#333", fg="#0f0", width=3, relief=tk.RIDGE)
            lbl.pack(side=tk.LEFT, padx=2)
            self.bit_labels_b.append(lbl)
        self.value_label_b = tk.Label(b_frame, text="= 0x00 (0)", font=("Courier", 10), bg="white")
        self.value_label_b.pack(side=tk.LEFT, padx=10)

        c_frame = ttk.Frame(bits_frame)
        c_frame.pack(fill=tk.X, pady=3)
        ttk.Label(c_frame, text="Carry:    ", font=("Courier", 10, "bold")).pack(side=tk.LEFT)
        self.bit_labels_c = []
        for i in range(7, -1, -1):
            lbl = tk.Label(c_frame, text="0", font=("Courier", 12, "bold"),
                          bg="#333", fg="#ff0", width=3, relief=tk.RIDGE)
            lbl.pack(side=tk.LEFT, padx=2)
            self.bit_labels_c.append(lbl)
        self.carry_out_label = tk.Label(c_frame, text="Cout: 0", font=("Courier", 10, "bold"), bg="lightyellow")
        self.carry_out_label.pack(side=tk.LEFT, padx=10)

        r_frame = ttk.Frame(bits_frame)
        r_frame.pack(fill=tk.X, pady=3)
        ttk.Label(r_frame, text="Result:   ", font=("Courier", 10, "bold")).pack(side=tk.LEFT)
        self.bit_labels_r = []
        for i in range(7, -1, -1):
            lbl = tk.Label(r_frame, text="0", font=("Courier", 12, "bold"),
                          bg="#333", fg="#0ff", width=3, relief=tk.RIDGE)
            lbl.pack(side=tk.LEFT, padx=2)
            self.bit_labels_r.append(lbl)
        self.value_label_r = tk.Label(r_frame, text="= 0x00 (0)", font=("Courier", 10), bg="white")
        self.value_label_r.pack(side=tk.LEFT, padx=10)

        log_frame = ttk.LabelFrame(main_frame, text="⚡ Gate Activity Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.gate_log = tk.Text(log_frame, height=6, font=("Courier", 8), bg="#000", fg="#0f0")
        self.gate_log.pack(fill=tk.BOTH, expand=True)

        self.draw_live_gates()

    def create_alu_control_visualization(self, parent):
        """Enhanced ALU visualization with live micro-operation display"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=5)

        ttk.Label(header_frame, text="⚙️ ALU & Control Unit - Live Data Flow",
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        self.alu_op_label = tk.Label(header_frame, text="Operation: IDLE",
                                     font=("Courier", 10, "bold"), bg="lightgray", padx=10)
        self.alu_op_label.pack(side=tk.RIGHT, padx=10)

        alu_frame = ttk.LabelFrame(main_frame, text="🧮 ALU Data Path Visualization", padding=10)
        alu_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.alu_canvas = tk.Canvas(alu_frame, bg="#0d1b2a", height=180, relief=tk.SUNKEN, bd=2)
        self.alu_canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_alu_diagram()

        micro_frame = ttk.LabelFrame(main_frame, text="📋 Micro-Operation Sequence", padding=10)
        micro_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.micro_op_canvas = tk.Canvas(micro_frame, bg="white", height=80, relief=tk.SUNKEN, bd=2)
        self.micro_op_canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_micro_op_pipeline()

        cu_frame = ttk.LabelFrame(main_frame, text="🎛️ Control Unit - Live Signals", padding=10)
        cu_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.cu_canvas = tk.Canvas(cu_frame, bg="#1b263b", height=100, relief=tk.SUNKEN, bd=2)
        self.cu_canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_cu_diagram()

        signals_frame = ttk.Frame(cu_frame)
        signals_frame.pack(fill=tk.X, pady=5)

        self.signal_labels = {}
        signal_names = ["RegWrite", "MemRead", "MemWrite", "ALUOp", "PCInc", "BusEnable"]
        for sig in signal_names:
            frame = ttk.Frame(signals_frame)
            frame.pack(side=tk.LEFT, padx=5)
            ttk.Label(frame, text=sig, font=("Courier", 8)).pack()
            lbl = tk.Label(frame, text="0", font=("Courier", 10, "bold"),
                          bg="#333", fg="#f00", width=3, relief=tk.SUNKEN)
            lbl.pack()
            self.signal_labels[sig] = lbl

    def draw_live_gates(self):
        """Draw animated full adder circuit on canvas"""
        canvas = self.gates_canvas
        canvas.delete("all")

        for i in range(8):
            x = 50 + i * 70
            y = 80

            canvas.create_rectangle(x, y, x+50, y+80, fill="#2d4263", outline="#00ff00", width=2)
            canvas.create_text(x+25, y+15, text=f"FA{i}", fill="#00ff00", font=("Courier", 9, "bold"))

            canvas.create_line(x+10, y-20, x+10, y, fill="#00ffff", width=2)
            canvas.create_text(x+10, y-25, text="A", fill="#00ffff", font=("Courier", 8))

            canvas.create_line(x+25, y-20, x+25, y, fill="#00ff00", width=2)
            canvas.create_text(x+25, y-25, text="B", fill="#00ff00", font=("Courier", 8))

            if i > 0:
                canvas.create_line(x-20, y+70, x, y+70, fill="#ffff00", width=2, arrow=tk.LAST)
            else:
                canvas.create_text(x-10, y+70, text="Cin=0", fill="#ffff00", font=("Courier", 7))

            canvas.create_line(x+25, y+80, x+25, y+110, fill="#00ffff", width=2, arrow=tk.LAST)
            canvas.create_text(x+25, y+115, text="S", fill="#00ffff", font=("Courier", 8))

            canvas.create_line(x+50, y+70, x+70, y+70, fill="#ffff00", width=2)

            canvas.create_text(x+25, y+40, text="XOR", fill="#aaa", font=("Courier", 7))
            canvas.create_text(x+25, y+55, text="AND", fill="#aaa", font=("Courier", 7))
            canvas.create_text(x+25, y+70, text="OR", fill="#aaa", font=("Courier", 7))

        canvas.create_text(300, 15, text="8-Bit Ripple Carry Adder - Full Adder Chain",
                          fill="#ffffff", font=("Arial", 11, "bold"))
        canvas.create_text(300, 185, text="← Carry propagates through chain →",
                          fill="#ffff00", font=("Courier", 9))

    def draw_micro_op_pipeline(self):
        """Draw micro-operation pipeline stages"""
        canvas = self.micro_op_canvas
        canvas.delete("all")

        stages = [
            ("FETCH", "#e74c3c", "PC→Addr"),
            ("DECODE", "#f39c12", "IR→Ctrl"),
            ("EXECUTE", "#27ae60", "ALU Op"),
            ("MEMORY", "#3498db", "Mem R/W"),
            ("WRITEBACK", "#9b59b6", "Reg←Result")
        ]

        for i, (name, color, desc) in enumerate(stages):
            x = 30 + i * 120
            y = 15

            fill_color = color if i == self.clock_phase else "#444"
            canvas.create_rectangle(x, y, x+100, y+50, fill=fill_color, outline="white", width=2)
            canvas.create_text(x+50, y+18, text=name, fill="white", font=("Arial", 10, "bold"))
            canvas.create_text(x+50, y+38, text=desc, fill="white", font=("Courier", 8))

            if i < len(stages) - 1:
                canvas.create_line(x+100, y+25, x+120, y+25, fill="white", width=2, arrow=tk.LAST)

    def draw_alu_diagram(self, val_a=0, val_b=0, result=0, op="ADD"):
        """Draw enhanced ALU diagram with live data values"""
        canvas = self.alu_canvas
        canvas.delete("all")

        canvas.create_rectangle(0, 0, 600, 180, fill="#0d1b2a", outline="")

        canvas.create_text(60, 15, text="Input A", fill="#00ffff", font=("Arial", 9, "bold"))
        canvas.create_rectangle(20, 30, 100, 55, fill="#1b4965", outline="#00ffff", width=2)
        canvas.create_text(60, 42, text=f"0x{val_a:02X}", fill="#00ffff", font=("Courier", 10, "bold"))

        canvas.create_line(100, 42, 150, 80, fill="#00ffff", width=2, arrow=tk.LAST)

        canvas.create_text(200, 15, text="Input B", fill="#00ff00", font=("Arial", 9, "bold"))
        canvas.create_rectangle(160, 30, 240, 55, fill="#1b4965", outline="#00ff00", width=2)
        canvas.create_text(200, 42, text=f"0x{val_b:02X}", fill="#00ff00", font=("Courier", 10, "bold"))

        canvas.create_line(200, 55, 200, 80, fill="#00ff00", width=2, arrow=tk.LAST)

        alu_points = [120, 80, 280, 80, 250, 140, 150, 140]
        canvas.create_polygon(alu_points, fill="#e63946", outline="#ffffff", width=3)
        canvas.create_text(200, 100, text=f"ALU: {op}", fill="white", font=("Arial", 12, "bold"))
        canvas.create_text(200, 120, text="⚡ Processing", fill="#ffff00", font=("Courier", 8))

        canvas.create_text(330, 40, text="Op Code", fill="#ffff00", font=("Arial", 9, "bold"))
        canvas.create_rectangle(300, 50, 360, 75, fill="#1b4965", outline="#ffff00", width=2)
        canvas.create_text(330, 62, text=op, fill="#ffff00", font=("Courier", 10, "bold"))
        canvas.create_line(300, 62, 280, 90, fill="#ffff00", width=2, arrow=tk.LAST)

        canvas.create_line(200, 140, 200, 160, fill="#ff6b6b", width=3, arrow=tk.LAST)
        canvas.create_rectangle(150, 160, 250, 180, fill="#1b4965", outline="#ff6b6b", width=2)
        canvas.create_text(200, 170, text=f"Result: 0x{result:02X} ({result})",
                          fill="#ff6b6b", font=("Courier", 10, "bold"))

        canvas.create_text(450, 100, text="FLAGS", fill="white", font=("Arial", 9, "bold"))
        flags = self.cpu.last_flags if self.cpu.last_flags else {'carry': 0, 'zero': 0, 'overflow': 0, 'sign': 0}
        flag_y = 115
        for flag_name, flag_val in [("C", flags.get('carry', 0)), ("Z", flags.get('zero', 0)),
                                     ("O", flags.get('overflow', 0)), ("S", flags.get('sign', 0))]:
            color = "#00ff00" if flag_val else "#ff0000"
            canvas.create_rectangle(420, flag_y, 440, flag_y+15, fill=color, outline="white")
            canvas.create_text(430, flag_y+7, text=flag_name, fill="white", font=("Courier", 8, "bold"))
            canvas.create_text(460, flag_y+7, text=str(flag_val), fill=color, font=("Courier", 9, "bold"))
            flag_y += 18

        canvas.create_line(250, 170, 500, 170, fill="#ff6b6b", width=2, dash=(5, 3))
        canvas.create_text(375, 160, text="→ Data Bus", fill="#aaa", font=("Courier", 8))

    def draw_cu_diagram(self, active_stage=0):
        """Draw control unit with highlighted active stage"""
        canvas = self.cu_canvas
        canvas.delete("all")

        stages = [
            (20, 20, "FETCH", "#e74c3c"),
            (120, 20, "DECODE", "#f39c12"),
            (220, 20, "EXECUTE", "#27ae60"),
            (320, 20, "MEM", "#3498db"),
            (420, 20, "WB", "#9b59b6"),
        ]

        for i, (x, y, title, color) in enumerate(stages):
            fill = color if i == active_stage else "#2d3436"
            outline_color = "#ffffff" if i == active_stage else "#636e72"
            width = 3 if i == active_stage else 1

            canvas.create_rectangle(x, y, x+80, y+55, fill=fill, outline=outline_color, width=width)
            canvas.create_text(x+40, y+20, text=title, fill="white", font=("Arial", 10, "bold"))

            canvas.create_text(x+40, y+40, text=f"T{i+1}", fill="#aaa", font=("Courier", 9))

            if i < len(stages) - 1:
                arrow_color = "#ffffff" if i == active_stage else "#636e72"
                canvas.create_line(x+80, y+27, x+120, y+27, fill=arrow_color, width=2, arrow=tk.LAST)

    def create_clock_visualization(self, parent):
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(main_frame, text="Clock & Timing Analysis",
                 font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=5)

        clock_frame = ttk.LabelFrame(main_frame, text="Clock Signal Visualization", padding=10)
        clock_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.clock_canvas = tk.Canvas(clock_frame, bg="#1a1a2e", height=120, relief=tk.SUNKEN, bd=2)
        self.clock_canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_clock_signal()

        timing_frame = ttk.LabelFrame(main_frame, text="📊 Data Flow Timing", padding=10)
        timing_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.timing_canvas = tk.Canvas(timing_frame, bg="#0d1b2a", height=150, relief=tk.SUNKEN, bd=2)
        self.timing_canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_timing_diagram()

        log_frame = ttk.LabelFrame(main_frame, text="📝 Execution Cycle Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.cycle_log = tk.Text(log_frame, height=8, font=("Courier", 9), bg="#000", fg="#0f0")
        self.cycle_log.pack(fill=tk.BOTH, expand=True)
        self.cycle_log.insert(tk.END, "Waiting for execution...\n")

    def draw_clock_signal(self, current_cycle=0):
        """Draw animated clock signal with current position highlighted"""
        canvas = self.clock_canvas
        canvas.delete("all")

        canvas.create_text(300, 15, text="Clock Signal - Rising Edge Triggered",
                         font=("Arial", 11, "bold"), fill="white")

        x_start = 30
        y_low = 90
        y_high = 45
        period = 60

        for i in range(8):
            x = x_start + i * period

            is_current = (i == current_cycle % 8)
            line_color = "#00ff00" if is_current else "#666"
            line_width = 3 if is_current else 2

            if i == 0:
                canvas.create_line(x, y_low, x, y_high, fill=line_color, width=line_width)

            canvas.create_line(x, y_high, x + period/2, y_high, fill=line_color, width=line_width)

            canvas.create_line(x + period/2, y_high, x + period/2, y_low, fill=line_color, width=line_width)

            canvas.create_line(x + period/2, y_low, x + period, y_low, fill=line_color, width=line_width)

            if i < 7:
                canvas.create_line(x + period, y_low, x + period, y_high, fill="#666", width=2)

            label_color = "#00ff00" if is_current else "#888"
            canvas.create_text(x + period/4, 110, text=f"T{i+1}", fill=label_color, font=("Courier", 9, "bold"))

            if is_current:
                canvas.create_oval(x + period/4 - 5, 25, x + period/4 + 5, 35, fill="#00ff00", outline="white")

        canvas.create_text(15, y_high, text="5V", fill="#0f0", font=("Courier", 9), anchor=tk.E)
        canvas.create_text(15, y_low, text="0V", fill="#f00", font=("Courier", 9), anchor=tk.E)

        canvas.create_text(550, 60, text=f"Cycle: {current_cycle}", fill="#ffff00", font=("Courier", 10, "bold"))

    def draw_timing_diagram(self, active_signals=None):
        """Draw data flow timing diagram with active signal highlighting"""
        if active_signals is None:
            active_signals = {}

        canvas = self.timing_canvas
        canvas.delete("all")

        canvas.create_text(300, 15, text="Data Flow Timing - Signal Activity",
                         font=("Arial", 11, "bold"), fill="white")

        signals = [
            ("Clock", 40, "#ffffff", "CLK"),
            ("Addr Bus", 65, "#00ffff", "ADDR"),
            ("Data Bus", 90, "#00ff00", "DATA"),
            ("Mem R/W", 115, "#ff6b6b", "MEM"),
            ("ALU", 140, "#ffd93d", "ALU"),
        ]

        x_start = 100
        period = 70

        for signal_name, y_offset, color, short in signals:
            is_active = active_signals.get(short, False)
            label_color = color if is_active else "#666"
            canvas.create_text(50, y_offset, text=signal_name, fill=label_color,
                             font=("Courier", 9, "bold"), anchor=tk.E)

            for cycle in range(6):
                x = x_start + cycle * period

                if signal_name == "Clock":
                    canvas.create_line(x, y_offset+8, x, y_offset-8, fill=color, width=2)
                    canvas.create_line(x, y_offset-8, x+period/2, y_offset-8, fill=color, width=2)
                    canvas.create_line(x+period/2, y_offset-8, x+period/2, y_offset+8, fill=color, width=2)
                    canvas.create_line(x+period/2, y_offset+8, x+period, y_offset+8, fill=color, width=2)
                else:
                    signal_color = color if (is_active and cycle == self.clock_phase % 6) else "#444"
                    canvas.create_rectangle(x+5, y_offset-6, x+period-5, y_offset+6,
                                          fill=signal_color, outline="#666")
                    if is_active and cycle == self.clock_phase % 6:
                        canvas.create_text(x+period/2, y_offset, text="●", fill="white",
                                         font=("Arial", 8, "bold"))

    def load_c_file(self):
        """Load C program from file"""
        file_path = filedialog.askopenfilename(filetypes=[("C Files", "*.c"), ("All", "*.*")])
        if file_path:
            with open(file_path, 'r') as f:
                code = f.read()
            self.code_editor.delete("1.0", tk.END)
            self.code_editor.insert("1.0", code)

    def compile_and_execute(self):
        """Compile C code with gcc and execute with CPU simulation"""
        c_code = self.code_editor.get("1.0", tk.END)

        if not c_code.strip():
            messagebox.showwarning("Warning", "No C code to compile")
            return

        self.reset_all()

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
                f.write(c_code)
                c_file = f.name

            exe_file = c_file.replace('.c', '')
            if os.name == 'nt':
                exe_file += '.exe'

            compile_result = subprocess.run(
                ['gcc', '-std=c99', '-o', exe_file, c_file],
                capture_output=True,
                text=True,
                timeout=10
            )

            if compile_result.returncode != 0:
                self.status_text.insert(tk.END, f"❌ Compilation Error:\n{compile_result.stderr}\n")
                os.unlink(c_file)
                return

            self.status_text.insert(tk.END, "✓ Compilation successful\n")
            self.status_text.insert(tk.END, "📍 Executing program...\n")
            self.status_text.see(tk.END)
            self.root.update()

            exec_result = subprocess.run(
                [exe_file],
                capture_output=True,
                text=True,
                timeout=5
            )

            self.simulate_program_execution(c_code, exec_result.stdout)

            os.unlink(c_file)
            os.unlink(exe_file)

        except subprocess.TimeoutExpired:
            self.status_text.insert(tk.END, "❌ Compilation/Execution timeout\n")
        except FileNotFoundError:
            self.status_text.insert(tk.END, "❌ gcc not found. Install gcc and try again.\n")
        except Exception as e:
            self.status_text.insert(tk.END, f"❌ Error: {str(e)}\n")

    def detect_program_type(self, c_code):
        """Detect the type of C program for appropriate simulation"""
        program_types = []

        embedded_patterns = [
            'ISR', 'interrupt', 'GPIO', 'HW_', 'volatile',
            'Watchdog', 'Timer', 'SysTick', 'while(1)', 'while (1)',
            'Debounce', 'superloop', 'uint8_t', 'uint16_t', 'uint32_t',
            '__WFI', 'PORTB', 'PORTC', 'PORTD', 'LED', 'Button'
        ]
        if any(pat in c_code for pat in embedded_patterns):
            program_types.append('EMBEDDED_MCU')

        if 'malloc' in c_code or 'calloc' in c_code or 'free(' in c_code:
            program_types.append('DYNAMIC_MEMORY')

        if '**' in c_code:
            program_types.append('DOUBLE_POINTER')

        if re.search(r'\*\s*\(\s*\w+\s*\+', c_code) or re.search(r'\w+\s*\+\+', c_code):
            program_types.append('POINTER_ARITHMETIC')

        if re.search(r'void\s+\w+\s*\([^)]*\*', c_code):
            program_types.append('PASS_BY_REFERENCE')

        if 'swap' in c_code.lower() and 'temp' in c_code:
            program_types.append('SWAP')

        if re.search(r'int\s*\*\s*\w+', c_code) and '&' in c_code:
            program_types.append('BASIC_POINTER')

        if re.search(r'int\s+\w+\s*\[\d+\]', c_code) and '*p' in c_code:
            program_types.append('ARRAY_POINTER')

        if 'arrayA' in c_code and 'arrayB' in c_code and 'result' in c_code:
            program_types.append('ARRAY_ADDITION')

        if not program_types:
            program_types.append('SIMPLE_VARS')

        return program_types

    def simulate_program_execution(self, c_code, program_output):
        """Simulate the C program execution on the CPU with visualization"""
        self.status_text.insert(tk.END, "\n📊 PROGRAM OUTPUT:\n")
        self.status_text.insert(tk.END, program_output)
        self.status_text.see(tk.END)
        self.root.update()

        program_types = self.detect_program_type(c_code)
        self.status_text.insert(tk.END, f"\n🔍 Detected program type(s): {', '.join(program_types)}\n")
        self.root.update()

        address = 0x00
        self.pointer_map = {}
        self.heap_start = 0x40
        self.heap_ptr = self.heap_start

        address = self.parse_and_allocate_variables(c_code, address)

        self.update_displays()
        self.root.update()

        if 'EMBEDDED_MCU' in program_types:
            self.simulate_embedded_mcu(c_code)
        elif 'ARRAY_ADDITION' in program_types:
            self.simulate_array_addition(c_code)
        elif 'BASIC_POINTER' in program_types:
            self.simulate_basic_pointer(c_code)
        elif 'ARRAY_POINTER' in program_types:
            self.simulate_array_pointer(c_code)
        elif 'SWAP' in program_types or 'PASS_BY_REFERENCE' in program_types:
            self.simulate_swap_function(c_code)
        elif 'DOUBLE_POINTER' in program_types:
            self.simulate_double_pointer(c_code)
        elif 'DYNAMIC_MEMORY' in program_types:
            self.simulate_dynamic_memory(c_code)
        else:
            self.simulate_simple_operations(c_code)

        self.update_displays()
        self.status_text.insert(tk.END, "\n✅ Execution completed\n")
        self.status_text.see(tk.END)
        self.root.update()

    def parse_and_allocate_variables(self, c_code, start_address):
        """Parse all variable declarations and allocate memory"""
        address = start_address

        array_pattern = r'int\s+(\w+)\s*\[(\d+)\]\s*=\s*\{([^}]+)\};'
        array_matches = re.findall(array_pattern, c_code)

        var_pattern = r'int\s+(\w+)\s*=\s*(\d+);'
        simple_matches = re.findall(var_pattern, c_code)

        ptr_pattern = r'int\s*\*\s*(\w+)\s*[;=]'
        ptr_matches = re.findall(ptr_pattern, c_code)

        double_ptr_pattern = r'int\s*\*\*\s*(\w+)\s*[;=]'
        double_ptr_matches = re.findall(double_ptr_pattern, c_code)

        for var_name, size, init_values in array_matches:
            clean_var = var_name.strip()
            values = [v.strip() for v in init_values.split(',')]

            self.c_program_memory[clean_var] = address

            for idx, val_str in enumerate(values):
                try:
                    val = int(val_str)
                    self.cpu.load_memory(address, val)
                    self.memory_allocations.append({
                        'name': f'{clean_var}[{idx}]',
                        'address': address,
                        'value': val,
                        'type': 'array_element'
                    })
                    if address < 8:
                        self.cpu.registers.write(address, val)
                    address += 1
                except ValueError:
                    address += 1

        for var_name, init_value in simple_matches:
            clean_var = var_name.strip()
            try:
                val = int(init_value.strip())
                self.cpu.load_memory(address, val)
                self.c_variables[clean_var] = val
                self.c_program_memory[clean_var] = address
                self.memory_allocations.append({
                    'name': clean_var,
                    'address': address,
                    'value': val,
                    'type': 'variable'
                })
                if address < 8:
                    self.cpu.registers.write(address, val)
                address += 1
            except (ValueError, IndexError):
                pass

        for ptr_name in ptr_matches:
            if ptr_name not in [m[0] for m in double_ptr_matches]:
                clean_ptr = ptr_name.strip()
                self.c_program_memory[clean_ptr] = address
                self.pointer_map[clean_ptr] = {'address': address, 'points_to': None}
                self.memory_allocations.append({
                    'name': f'*{clean_ptr}',
                    'address': address,
                    'value': 0,
                    'type': 'pointer'
                })
                address += 1

        for ptr_name in double_ptr_matches:
            clean_ptr = ptr_name.strip()
            self.c_program_memory[clean_ptr] = address
            self.pointer_map[clean_ptr] = {'address': address, 'points_to': None, 'is_double': True}
            self.memory_allocations.append({
                'name': f'**{clean_ptr}',
                'address': address,
                'value': 0,
                'type': 'double_pointer'
            })
            address += 1

        return address

    def simulate_array_addition(self, c_code):
        """Simulate array addition operations with synchronized visualization"""
        self.status_text.insert(tk.END, "\n🔄 Simulating Array Addition Operations:\n")
        self.root.update()

        array_a = self.c_program_memory.get('arrayA', 0x00)
        array_b = self.c_program_memory.get('arrayB', 0x00)
        result_addr = self.c_program_memory.get('result', 0x10)

        for i in range(5):
            addr_a = array_a + i
            addr_b = array_b + i
            addr_r = result_addr + i

            self.clock_phase = 0
            val_a = self.cpu.read_memory(addr_a)
            val_a_bits = self.cpu._int_to_bits(val_a)

            self.status_text.insert(tk.END, f"  Step {i+1}: READ [0x{addr_a:02X}]={val_a} (arrayA[{i}])\n")
            self.status_text.see(tk.END)
            self.sync_visualizations(val_a, 0, 0, "FETCH_A")
            time.sleep(0.4)

            self.clock_phase = 1
            val_b = self.cpu.read_memory(addr_b)
            val_b_bits = self.cpu._int_to_bits(val_b)

            self.status_text.insert(tk.END, f"       READ [0x{addr_b:02X}]={val_b} (arrayB[{i}])\n")
            self.status_text.see(tk.END)
            self.sync_visualizations(val_a, val_b, 0, "FETCH_B")
            time.sleep(0.4)

            self.clock_phase = 2
            result_bits, flags = self.cpu.alu.execute(val_a_bits, val_b_bits, 0)
            result_val = self.cpu._bits_to_int(result_bits[:8])

            self.cpu.load_memory(addr_r, result_val)
            self.cpu.last_result = result_val
            self.cpu.last_flags = flags

            self.status_text.insert(tk.END, f"       ALU: {val_a} + {val_b} = {result_val}\n")
            self.status_text.insert(tk.END, f"       WRITE [0x{addr_r:02X}]={result_val} (result[{i}])\n")
            self.status_text.see(tk.END)

            self.sync_visualizations(val_a, val_b, result_val, "ALU_ADD")
            time.sleep(0.3)

    def simulate_basic_pointer(self, c_code):
        """Simulate basic pointer operations: int *p = &a; *p = value;"""
        self.status_text.insert(tk.END, "\n📍 Simulating Basic Pointer Operations:\n")
        self.root.update()

        var_match = re.search(r'int\s+(\w+)\s*=\s*(\d+);', c_code)
        ptr_match = re.search(r'(\w+)\s*=\s*&(\w+);', c_code)

        if var_match and ptr_match:
            var_name = var_match.group(1)
            var_value = int(var_match.group(2))
            ptr_name = ptr_match.group(1)
            target_var = ptr_match.group(2)

            var_addr = self.c_program_memory.get(var_name, 0x00)
            ptr_addr = self.c_program_memory.get(ptr_name, 0x01)

            self.clock_phase = 0
            self.status_text.insert(tk.END, f"\n  Step 1: Variable '{var_name}' allocated\n")
            self.status_text.insert(tk.END, f"          Address: 0x{var_addr:02X}\n")
            self.status_text.insert(tk.END, f"          Value: {var_value}\n")
            self.cpu.load_memory(var_addr, var_value)
            self.sync_visualizations(var_value, var_addr, var_value, "VAR_ALLOC")
            time.sleep(0.5)

            self.clock_phase = 1
            self.status_text.insert(tk.END, f"\n  Step 2: Pointer '{ptr_name}' = &{target_var}\n")
            self.status_text.insert(tk.END, f"          Pointer address: 0x{ptr_addr:02X}\n")
            self.status_text.insert(tk.END, f"          Stores address: 0x{var_addr:02X} (address of {target_var})\n")
            self.cpu.load_memory(ptr_addr, var_addr)
            self.pointer_map[ptr_name] = {'address': ptr_addr, 'points_to': var_addr}
            self.sync_visualizations(var_addr, ptr_addr, var_addr, "PTR_STORE")
            time.sleep(0.5)

            self.clock_phase = 2
            self.status_text.insert(tk.END, f"\n  Step 3: Dereferencing *{ptr_name}\n")
            self.status_text.insert(tk.END, f"          Read pointer value: 0x{var_addr:02X}\n")
            self.status_text.insert(tk.END, f"          Go to address 0x{var_addr:02X}\n")
            self.status_text.insert(tk.END, f"          Read value: {var_value}\n")
            self.sync_visualizations(ptr_addr, var_addr, var_value, "PTR_DEREF")
            time.sleep(0.5)

            self.status_text.insert(tk.END, f"\n  📊 Memory Layout:\n")
            self.status_text.insert(tk.END, f"     ┌─────────────────────────────────────┐\n")
            self.status_text.insert(tk.END, f"     │ [{ptr_name}] @ 0x{ptr_addr:02X} = 0x{var_addr:02X} ──────┐    │\n")
            self.status_text.insert(tk.END, f"     │                              │    │\n")
            self.status_text.insert(tk.END, f"     │                              ▼    │\n")
            self.status_text.insert(tk.END, f"     │ [{var_name}]  @ 0x{var_addr:02X} = {var_value:3d}       │\n")
            self.status_text.insert(tk.END, f"     └─────────────────────────────────────┘\n")
            self.root.update()

    def simulate_array_pointer(self, c_code):
        """Simulate pointer arithmetic with arrays"""
        self.status_text.insert(tk.END, "\n🔢 Simulating Array Pointer Traversal:\n")
        self.root.update()

        array_match = re.search(r'int\s+(\w+)\s*\[(\d+)\]\s*=\s*\{([^}]+)\};', c_code)

        if array_match:
            arr_name = array_match.group(1)
            arr_size = int(array_match.group(2))
            values = [int(v.strip()) for v in array_match.group(3).split(',')]

            arr_base = self.c_program_memory.get(arr_name, 0x00)

            self.status_text.insert(tk.END, f"\n  Array '{arr_name}' base address: 0x{arr_base:02X}\n")
            self.status_text.insert(tk.END, f"  Pointer p = arr (points to &arr[0])\n\n")
            self.root.update()
            time.sleep(0.3)

            for i in range(min(len(values), arr_size)):
                self.clock_phase = i % 5
                addr = arr_base + i
                val = values[i]

                self.status_text.insert(tk.END, f"  Step {i+1}: *(p + {i}) = *(0x{arr_base:02X} + {i})\n")
                self.status_text.insert(tk.END, f"          = *0x{addr:02X}\n")
                self.status_text.insert(tk.END, f"          = {val}\n")
                self.status_text.insert(tk.END, f"          (arr[{i}] = {val})\n\n")

                self.cpu.address_bus.set_address("CPU", addr)
                self.cpu.data_bus.transfer("MEMORY", val, "CPU")
                self.sync_visualizations(arr_base + i, addr, val, "PTR_ARITH")
                time.sleep(0.4)

            self.status_text.insert(tk.END, f"\n  📊 Pointer Arithmetic Visualization:\n")
            self.status_text.insert(tk.END, f"     p ──────────────────────────────────────┐\n")
            self.status_text.insert(tk.END, f"                                             ▼\n")
            for i, val in enumerate(values[:5]):
                arrow = "◄── p" if i == 0 else f"◄── p+{i}"
                self.status_text.insert(tk.END, f"     [0x{arr_base+i:02X}] = {val:3d}  {arrow}\n")
            self.root.update()

    def simulate_swap_function(self, c_code):
        """Simulate swap function with pass by reference"""
        self.status_text.insert(tk.END, "\n🔄 Simulating Swap Function (Pass by Reference):\n")
        self.root.update()

        var_match = re.findall(r'int\s+(\w+)\s*=\s*(\d+)', c_code)

        if len(var_match) >= 2:
            var_a, val_a = var_match[0][0], int(var_match[0][1])
            var_b, val_b = var_match[1][0], int(var_match[1][1])

            addr_a = self.c_program_memory.get(var_a, 0x00)
            addr_b = self.c_program_memory.get(var_b, 0x01)

            self.status_text.insert(tk.END, f"\n  Initial State:\n")
            self.status_text.insert(tk.END, f"    {var_a} @ 0x{addr_a:02X} = {val_a}\n")
            self.status_text.insert(tk.END, f"    {var_b} @ 0x{addr_b:02X} = {val_b}\n")
            self.cpu.load_memory(addr_a, val_a)
            self.cpu.load_memory(addr_b, val_b)
            self.sync_visualizations(val_a, addr_a, val_b, "INIT")
            time.sleep(0.5)

            self.clock_phase = 0
            self.status_text.insert(tk.END, f"\n  Step 1: Call swap(&{var_a}, &{var_b})\n")
            self.status_text.insert(tk.END, f"          Push &{var_a} = 0x{addr_a:02X} to stack\n")
            self.status_text.insert(tk.END, f"          Push &{var_b} = 0x{addr_b:02X} to stack\n")
            self.sync_visualizations(addr_a, addr_b, 0, "PUSH_ADDR")
            time.sleep(0.4)

            self.clock_phase = 1
            temp_val = val_a
            self.status_text.insert(tk.END, f"\n  Step 2: temp = *x\n")
            self.status_text.insert(tk.END, f"          Read from *0x{addr_a:02X} = {temp_val}\n")
            self.status_text.insert(tk.END, f"          temp = {temp_val}\n")
            self.sync_visualizations(addr_a, 0xFE, temp_val, "READ")
            time.sleep(0.4)

            self.clock_phase = 2
            self.status_text.insert(tk.END, f"\n  Step 3: *x = *y\n")
            self.status_text.insert(tk.END, f"          Read from *0x{addr_b:02X} = {val_b}\n")
            self.status_text.insert(tk.END, f"          Write to *0x{addr_a:02X} = {val_b}\n")
            self.cpu.load_memory(addr_a, val_b)
            self.sync_visualizations(val_b, addr_a, val_b, "WRITE")
            time.sleep(0.4)

            self.clock_phase = 3
            self.status_text.insert(tk.END, f"\n  Step 4: *y = temp\n")
            self.status_text.insert(tk.END, f"          Write to *0x{addr_b:02X} = {temp_val}\n")
            self.cpu.load_memory(addr_b, temp_val)
            self.sync_visualizations(temp_val, addr_b, temp_val, "WRITE")
            time.sleep(0.4)

            self.status_text.insert(tk.END, f"\n  ✅ After Swap:\n")
            self.status_text.insert(tk.END, f"    {var_a} @ 0x{addr_a:02X} = {val_b} (was {val_a})\n")
            self.status_text.insert(tk.END, f"    {var_b} @ 0x{addr_b:02X} = {temp_val} (was {val_b})\n")

            self.status_text.insert(tk.END, f"\n  📊 Swap Visualization:\n")
            self.status_text.insert(tk.END, f"     BEFORE          AFTER\n")
            self.status_text.insert(tk.END, f"     {var_a}={val_a:3d}    ───►    {var_a}={val_b:3d}\n")
            self.status_text.insert(tk.END, f"         ╲      ╱\n")
            self.status_text.insert(tk.END, f"          ╲    ╱\n")
            self.status_text.insert(tk.END, f"           ╲  ╱\n")
            self.status_text.insert(tk.END, f"            ╲╱\n")
            self.status_text.insert(tk.END, f"            ╱╲\n")
            self.status_text.insert(tk.END, f"           ╱  ╲\n")
            self.status_text.insert(tk.END, f"          ╱    ╲\n")
            self.status_text.insert(tk.END, f"         ╱      ╲\n")
            self.status_text.insert(tk.END, f"     {var_b}={val_b:3d}    ───►    {var_b}={temp_val:3d}\n")
            self.root.update()

    def simulate_double_pointer(self, c_code):
        """Simulate double pointer operations"""
        self.status_text.insert(tk.END, "\n📍📍 Simulating Double Pointer Operations:\n")
        self.root.update()

        var_match = re.search(r'int\s+(\w+)\s*=\s*(\d+);', c_code)

        if var_match:
            var_name = var_match.group(1)
            var_value = int(var_match.group(2))

            var_addr = 0x00
            ptr_addr = 0x01
            dptr_addr = 0x02

            self.clock_phase = 0
            self.status_text.insert(tk.END, f"\n  Step 1: int {var_name} = {var_value}\n")
            self.status_text.insert(tk.END, f"          {var_name} @ address 0x{var_addr:02X} = {var_value}\n")
            self.cpu.load_memory(var_addr, var_value)
            self.c_program_memory[var_name] = var_addr
            self.sync_visualizations(var_value, var_addr, var_value, "VAR_ALLOC")
            time.sleep(0.5)

            self.clock_phase = 1
            self.status_text.insert(tk.END, f"\n  Step 2: int *p = &{var_name}\n")
            self.status_text.insert(tk.END, f"          p @ address 0x{ptr_addr:02X}\n")
            self.status_text.insert(tk.END, f"          p stores: 0x{var_addr:02X} (address of {var_name})\n")
            self.cpu.load_memory(ptr_addr, var_addr)
            self.sync_visualizations(var_addr, ptr_addr, var_addr, "PTR_STORE")
            time.sleep(0.5)

            self.clock_phase = 2
            self.status_text.insert(tk.END, f"\n  Step 3: int **pp = &p\n")
            self.status_text.insert(tk.END, f"          pp @ address 0x{dptr_addr:02X}\n")
            self.status_text.insert(tk.END, f"          pp stores: 0x{ptr_addr:02X} (address of p)\n")
            self.cpu.load_memory(dptr_addr, ptr_addr)
            self.sync_visualizations(ptr_addr, dptr_addr, ptr_addr, "DPTR_STORE")
            time.sleep(0.5)

            self.clock_phase = 3
            self.status_text.insert(tk.END, f"\n  Step 4: Dereferencing Chain:\n")
            self.status_text.insert(tk.END, f"          **pp = *(*pp)\n")
            self.status_text.insert(tk.END, f"               = *(value at 0x{dptr_addr:02X})\n")
            self.status_text.insert(tk.END, f"               = *(0x{ptr_addr:02X})\n")
            self.status_text.insert(tk.END, f"               = value at 0x{ptr_addr:02X}\n")
            self.status_text.insert(tk.END, f"               = 0x{var_addr:02X}\n")
            self.status_text.insert(tk.END, f"          Then: *(0x{var_addr:02X}) = {var_value}\n")
            self.sync_visualizations(dptr_addr, var_addr, var_value, "DPTR_DEREF")
            time.sleep(0.5)

            self.status_text.insert(tk.END, f"\n  📊 Double Pointer Chain:\n")
            self.status_text.insert(tk.END, f"     ┌──────────────────────────────────────────────┐\n")
            self.status_text.insert(tk.END, f"     │  pp @ 0x{dptr_addr:02X}                                 │\n")
            self.status_text.insert(tk.END, f"     │  ┌────────┐                                  │\n")
            self.status_text.insert(tk.END, f"     │  │ 0x{ptr_addr:02X}   │──────┐                         │\n")
            self.status_text.insert(tk.END, f"     │  └────────┘      │                         │\n")
            self.status_text.insert(tk.END, f"     │                  ▼                         │\n")
            self.status_text.insert(tk.END, f"     │  p @ 0x{ptr_addr:02X}                                  │\n")
            self.status_text.insert(tk.END, f"     │  ┌────────┐                                  │\n")
            self.status_text.insert(tk.END, f"     │  │ 0x{var_addr:02X}   │──────┐                         │\n")
            self.status_text.insert(tk.END, f"     │  └────────┘      │                         │\n")
            self.status_text.insert(tk.END, f"     │                  ▼                         │\n")
            self.status_text.insert(tk.END, f"     │  {var_name} @ 0x{var_addr:02X}                                  │\n")
            self.status_text.insert(tk.END, f"     │  ┌────────┐                                  │\n")
            self.status_text.insert(tk.END, f"     │  │  {var_value:3d}   │ ◄── actual value             │\n")
            self.status_text.insert(tk.END, f"     │  └────────┘                                  │\n")
            self.status_text.insert(tk.END, f"     └──────────────────────────────────────────────┘\n")
            self.root.update()

    def simulate_dynamic_memory(self, c_code):
        """Simulate malloc/free operations"""
        self.status_text.insert(tk.END, "\n🧱 Simulating Dynamic Memory Allocation:\n")
        self.root.update()

        malloc_match = re.search(r'malloc\s*\(\s*sizeof\s*\(\s*int\s*\)\s*\)', c_code)
        value_match = re.search(r'\*\s*\w+\s*=\s*(\d+)', c_code)

        ptr_addr = 0x00
        heap_addr = self.heap_start

        self.clock_phase = 0
        self.status_text.insert(tk.END, f"\n  Step 1: p = (int*)malloc(sizeof(int))\n")
        self.status_text.insert(tk.END, f"          Request: {4} bytes from heap\n")
        self.status_text.insert(tk.END, f"          Heap allocator finds free block...\n")
        self.sync_visualizations(4, 0, 0, "MALLOC_REQ")
        time.sleep(0.5)

        self.clock_phase = 1
        self.status_text.insert(tk.END, f"\n  Step 2: Memory allocated at 0x{heap_addr:02X}\n")
        self.status_text.insert(tk.END, f"          Pointer p @ 0x{ptr_addr:02X} = 0x{heap_addr:02X}\n")
        self.cpu.load_memory(ptr_addr, heap_addr)
        self.sync_visualizations(heap_addr, ptr_addr, heap_addr, "MALLOC_DONE")
        time.sleep(0.5)

        if value_match:
            value = int(value_match.group(1))
            self.clock_phase = 2
            self.status_text.insert(tk.END, f"\n  Step 3: *p = {value}\n")
            self.status_text.insert(tk.END, f"          Dereference p: go to 0x{heap_addr:02X}\n")
            self.status_text.insert(tk.END, f"          Store {value} at heap address 0x{heap_addr:02X}\n")
            self.cpu.load_memory(heap_addr, value)
            self.sync_visualizations(value, heap_addr, value, "HEAP_WRITE")
            time.sleep(0.5)

        self.clock_phase = 3
        self.status_text.insert(tk.END, f"\n  Step 4: free(p)\n")
        self.status_text.insert(tk.END, f"          Release memory at 0x{heap_addr:02X}\n")
        self.status_text.insert(tk.END, f"          Memory returned to heap\n")
        self.status_text.insert(tk.END, f"          ⚠️  p is now a dangling pointer!\n")
        self.sync_visualizations(0, heap_addr, 0, "FREE")
        time.sleep(0.5)

        self.status_text.insert(tk.END, f"\n  📊 Memory Layout:\n")
        self.status_text.insert(tk.END, f"     ┌───────────────────────────────────────────┐\n")
        self.status_text.insert(tk.END, f"     │  STACK (0x00-0x3F)                        │\n")
        self.status_text.insert(tk.END, f"     │  ┌────────────────────────────────────┐   │\n")
        self.status_text.insert(tk.END, f"     │  │ p @ 0x{ptr_addr:02X} = 0x{heap_addr:02X}                │   │\n")
        self.status_text.insert(tk.END, f"     │  └────────────────────────────────────┘   │\n")
        self.status_text.insert(tk.END, f"     │                    │                      │\n")
        self.status_text.insert(tk.END, f"     │                    │ (pointer)            │\n")
        self.status_text.insert(tk.END, f"     │                    ▼                      │\n")
        self.status_text.insert(tk.END, f"     ├───────────────────────────────────────────┤\n")
        self.status_text.insert(tk.END, f"     │  HEAP (0x40-0x7F)                         │\n")
        self.status_text.insert(tk.END, f"     │  ┌────────────────────────────────────┐   │\n")
        if value_match:
            self.status_text.insert(tk.END, f"     │  │ @ 0x{heap_addr:02X} = {value:3d} (allocated)       │   │\n")
        self.status_text.insert(tk.END, f"     │  └────────────────────────────────────┘   │\n")
        self.status_text.insert(tk.END, f"     └───────────────────────────────────────────┘\n")
        self.root.update()

    def simulate_simple_operations(self, c_code):
        """Simulate simple variable operations"""
        self.status_text.insert(tk.END, "\n📝 Simulating Simple Variable Operations:\n")
        self.root.update()

        for alloc in self.memory_allocations:
            self.status_text.insert(tk.END, f"  {alloc['name']} @ 0x{alloc['address']:02X} = {alloc['value']}\n")
            self.sync_visualizations(alloc['value'], 0, alloc['value'], "LOAD")
            time.sleep(0.2)

    def simulate_embedded_mcu(self, c_code):
        """Simulate embedded/MCU program with superloop, ISR, GPIO, timers"""
        self.status_text.insert(tk.END, "\n🔌 Simulating Embedded MCU Program:\n")
        self.status_text.insert(tk.END, "="*50 + "\n")
        self.root.update()

        has_timer = 'SysTick' in c_code or 'Timer' in c_code or '1ms' in c_code
        has_gpio = 'LED' in c_code or 'GPIO' in c_code or 'HW_Led' in c_code
        has_button = 'Button' in c_code or 'btn' in c_code
        has_watchdog = 'Watchdog' in c_code or 'WDT' in c_code
        has_debounce = 'Debounce' in c_code or 'debounce' in c_code
        has_superloop = 'while(1)' in c_code or 'while (1)' in c_code

        GPIO_ADDR = 0x20
        TIMER_ADDR = 0x21
        WDT_ADDR = 0x22
        BTN_ADDR = 0x23
        LED_ADDR = 0x24

        self.cpu.load_memory(GPIO_ADDR, 0x00)
        self.cpu.load_memory(TIMER_ADDR, 0x00)
        self.cpu.load_memory(WDT_ADDR, 0xFF)
        self.cpu.load_memory(BTN_ADDR, 0x00)
        self.cpu.load_memory(LED_ADDR, 0x00)

        self.status_text.insert(tk.END, "\n🔧 Phase 1: Hardware Initialization\n")
        self.status_text.insert(tk.END, "-"*40 + "\n")
        self.clock_phase = 0
        self.sync_visualizations(0, 0, 0, "INIT")

        self.status_text.insert(tk.END, "  → HW_Init() called\n")
        self.status_text.insert(tk.END, "    • Configure system clock\n")
        self.log_clock_cycle("FETCH", "HW_Init function address")
        time.sleep(0.3)

        self.status_text.insert(tk.END, "    • Initialize GPIO ports\n")
        self.cpu.load_memory(GPIO_ADDR, 0x00)
        self.log_clock_cycle("EXECUTE", "GPIO registers cleared")
        self.sync_visualizations(0x00, GPIO_ADDR, 0x00, "GPIO_INIT")
        time.sleep(0.3)

        if has_watchdog:
            self.status_text.insert(tk.END, "    • Enable Watchdog Timer\n")
            self.cpu.load_memory(WDT_ADDR, 0xFF)
            self.log_clock_cycle("EXECUTE", "WDT counter = 0xFF")
            time.sleep(0.2)

        self.update_displays()
        self.root.update()
        time.sleep(0.3)

        if has_timer:
            self.status_text.insert(tk.END, "\n⏱️ Phase 2: Timer Configuration\n")
            self.status_text.insert(tk.END, "-"*40 + "\n")
            self.clock_phase = 1

            self.status_text.insert(tk.END, "  → HW_Enable1msTickTimerIRQ()\n")
            self.status_text.insert(tk.END, "    • Configure timer for 1ms period\n")
            self.log_clock_cycle("FETCH", "Timer config routine")
            time.sleep(0.2)

            self.status_text.insert(tk.END, "    • Enable timer interrupt (NVIC)\n")
            self.timer_state['enabled'] = True
            self.log_clock_cycle("EXECUTE", "Timer IRQ enabled")
            self.sync_visualizations(0x01, TIMER_ADDR, 0x01, "TIMER_EN")
            time.sleep(0.3)

            self.update_displays()
            self.root.update()

        if has_superloop:
            self.status_text.insert(tk.END, "\n🔄 Phase 3: Main Superloop Execution\n")
            self.status_text.insert(tk.END, "-"*40 + "\n")
            self.status_text.insert(tk.END, "  Entering while(1) superloop...\n\n")
            self.root.update()

            for iteration in range(5):
                ms_tick = iteration * 5
                self.timer_state['ms'] = ms_tick

                self.status_text.insert(tk.END, f"  ┌─ Iteration {iteration+1} (t = {ms_tick}ms) ─────────────────┐\n")
                self.root.update()

                if has_timer and iteration > 0:
                    self.clock_phase = 0
                    self.isr_state['active'] = True
                    self.isr_state['name'] = 'SysTick_1ms_ISR'

                    self.status_text.insert(tk.END, f"  │ ⚡ ISR: SysTick_1ms_ISR()\n")
                    self.status_text.insert(tk.END, f"  │    • Push context to stack\n")
                    self.log_clock_cycle("ISR_ENTRY", "Context saved")
                    self.sync_visualizations(ms_tick, 0x80, ms_tick, "ISR")
                    time.sleep(0.2)

                    self.status_text.insert(tk.END, f"  │    • g_ms++ → {ms_tick}\n")
                    self.cpu.load_memory(TIMER_ADDR, ms_tick & 0xFF)
                    self.log_clock_cycle("EXECUTE", f"g_ms = {ms_tick}")
                    time.sleep(0.2)

                    self.status_text.insert(tk.END, f"  │    • Pop context, return\n")
                    self.isr_state['active'] = False
                    self.log_clock_cycle("ISR_EXIT", "Context restored")
                    time.sleep(0.2)

                if has_button:
                    self.clock_phase = 1
                    self.status_text.insert(tk.END, f"  │ 🔘 ButtonTask_5ms()\n")

                    raw_btn = 1 if iteration >= 2 else 0
                    self.cpu.load_memory(BTN_ADDR, raw_btn)

                    self.status_text.insert(tk.END, f"  │    • Read raw button: {raw_btn}\n")
                    self.log_clock_cycle("FETCH", f"BTN pin = {raw_btn}")
                    self.sync_visualizations(raw_btn, BTN_ADDR, raw_btn, "GPIO_READ")
                    time.sleep(0.2)

                    if has_debounce:
                        self.debounce_state['raw'] = raw_btn
                        if raw_btn == self.debounce_state.get('last_raw', 0):
                            self.debounce_state['count'] = min(4, self.debounce_state.get('count', 0) + 1)
                        else:
                            self.debounce_state['count'] = 0

                        if self.debounce_state['count'] >= 4:
                            self.debounce_state['stable'] = raw_btn
                            self.status_text.insert(tk.END, f"  │    • Debounce: stable={raw_btn} (count≥4)\n")
                        else:
                            self.status_text.insert(tk.END, f"  │    • Debounce: cnt={self.debounce_state['count']}/4\n")

                        self.debounce_state['last_raw'] = raw_btn
                        self.log_clock_cycle("EXECUTE", f"Debounce logic")
                        time.sleep(0.2)

                    if iteration == 3:
                        self.status_text.insert(tk.END, f"  │ 💡 ButtonActionTask()\n")
                        self.status_text.insert(tk.END, f"  │    • Rising edge detected!\n")
                        led_state = self.cpu.read_memory(LED_ADDR)
                        led_state = 1 - led_state
                        self.cpu.load_memory(LED_ADDR, led_state)
                        self.status_text.insert(tk.END, f"  │    • HW_LedToggle() → LED = {led_state}\n")
                        self.log_clock_cycle("EXECUTE", f"LED = {led_state}")
                        self.sync_visualizations(led_state, LED_ADDR, led_state, "GPIO_WRITE")
                        self.gpio_state['LED'] = led_state
                        time.sleep(0.2)

                if has_gpio and iteration == 4:
                    self.clock_phase = 2
                    self.status_text.insert(tk.END, f"  │ 💡 LedBlinkTask_500ms()\n")
                    led_state = self.cpu.read_memory(LED_ADDR)
                    led_state = 1 - led_state
                    self.cpu.load_memory(LED_ADDR, led_state)
                    self.status_text.insert(tk.END, f"  │    • Toggle LED → {led_state}\n")
                    self.log_clock_cycle("EXECUTE", f"LED toggled to {led_state}")
                    self.sync_visualizations(led_state, LED_ADDR, led_state, "GPIO_WRITE")
                    time.sleep(0.2)

                if has_watchdog and iteration % 2 == 0:
                    self.clock_phase = 3
                    self.status_text.insert(tk.END, f"  │ 🐕 HeartbeatTask_100ms()\n")
                    self.cpu.load_memory(WDT_ADDR, 0xFF)
                    self.status_text.insert(tk.END, f"  │    • HW_WatchdogKick() → WDT reset\n")
                    self.log_clock_cycle("EXECUTE", "WDT refreshed")
                    self.sync_visualizations(0xFF, WDT_ADDR, 0xFF, "WDT_KICK")
                    time.sleep(0.2)

                self.status_text.insert(tk.END, f"  │ → Loop back to while(1)\n")
                self.status_text.insert(tk.END, f"  └──────────────────────────────────────┘\n\n")
                self.update_displays()
                self.root.update()
                time.sleep(0.3)

        self.status_text.insert(tk.END, "\n📊 Final Hardware State:\n")
        self.status_text.insert(tk.END, "="*50 + "\n")
        self.status_text.insert(tk.END, f"  GPIO Register  [0x{GPIO_ADDR:02X}] = 0x{self.cpu.read_memory(GPIO_ADDR):02X}\n")
        self.status_text.insert(tk.END, f"  Timer Counter  [0x{TIMER_ADDR:02X}] = {self.cpu.read_memory(TIMER_ADDR)} ms\n")
        self.status_text.insert(tk.END, f"  Watchdog       [0x{WDT_ADDR:02X}] = 0x{self.cpu.read_memory(WDT_ADDR):02X}\n")
        self.status_text.insert(tk.END, f"  Button State   [0x{BTN_ADDR:02X}] = {self.cpu.read_memory(BTN_ADDR)}\n")
        self.status_text.insert(tk.END, f"  LED State      [0x{LED_ADDR:02X}] = {self.cpu.read_memory(LED_ADDR)}\n")

        self.status_text.insert(tk.END, "\n📍 Memory Map:\n")
        self.status_text.insert(tk.END, "  ┌─────────────────────────────────────────┐\n")
        self.status_text.insert(tk.END, "  │ 0x00-0x1F: Program Variables (RAM)      │\n")
        self.status_text.insert(tk.END, "  │ 0x20-0x2F: I/O Registers (GPIO/Timer)   │\n")
        self.status_text.insert(tk.END, "  │ 0x80-0xFF: Stack                        │\n")
        self.status_text.insert(tk.END, "  └─────────────────────────────────────────┘\n")
        self.root.update()

    def log_clock_cycle(self, phase, description):
        """Log a clock cycle to the timing tab"""
        try:
            if hasattr(self, 'cycle_log'):
                self.cycle_log.insert(tk.END, f"[T{self.cpu.cycles:03d}] {phase:12s}: {description}\n")
                self.cycle_log.see(tk.END)
        except:
            pass

    def sync_visualizations(self, val_a, val_b, result, operation):
        """Synchronize all visualization tabs with current operation"""
        try:
            self.cpu.cycles += 1
            self.cpu.last_result = result

            val_a_bits = self.cpu._int_to_bits(val_a if isinstance(val_a, int) else 0)
            val_b_bits = self.cpu._int_to_bits(val_b if isinstance(val_b, int) else 0)
            result_bits = self.cpu._int_to_bits(result if isinstance(result, int) else 0)

            self.current_alu_bits = {'a': val_a_bits, 'b': val_b_bits, 'result': result_bits}

            self.update_gates_tab(val_a_bits, val_b_bits, result_bits, operation)

            self.update_alu_tab(val_a, val_b, result, operation)

            self.update_clock_tab(operation)

            self.update_displays()
            self.root.update()

        except Exception as e:
            pass

    def update_gates_tab(self, a_bits, b_bits, result_bits, operation):
        """Update the Gates & Logic tab with current bit values"""
        try:
            for i in range(8):
                idx = 7 - i

                if hasattr(self, 'bit_labels_a') and i < len(self.bit_labels_a):
                    bit_val = a_bits[idx] if idx < len(a_bits) else 0
                    self.bit_labels_a[i].config(
                        text=str(bit_val),
                        fg="#0f0" if bit_val else "#333",
                        bg="#0a0" if bit_val else "#333"
                    )

                if hasattr(self, 'bit_labels_b') and i < len(self.bit_labels_b):
                    bit_val = b_bits[idx] if idx < len(b_bits) else 0
                    self.bit_labels_b[i].config(
                        text=str(bit_val),
                        fg="#0f0" if bit_val else "#333",
                        bg="#0a0" if bit_val else "#333"
                    )

                if hasattr(self, 'bit_labels_r') and i < len(self.bit_labels_r):
                    bit_val = result_bits[idx] if idx < len(result_bits) else 0
                    self.bit_labels_r[i].config(
                        text=str(bit_val),
                        fg="#0ff" if bit_val else "#333",
                        bg="#066" if bit_val else "#333"
                    )

            val_a = sum(a_bits[i] * (2**i) for i in range(min(8, len(a_bits))))
            val_b = sum(b_bits[i] * (2**i) for i in range(min(8, len(b_bits))))
            val_r = sum(result_bits[i] * (2**i) for i in range(min(8, len(result_bits))))

            if hasattr(self, 'value_label_a'):
                self.value_label_a.config(text=f"= 0x{val_a:02X} ({val_a})")
            if hasattr(self, 'value_label_b'):
                self.value_label_b.config(text=f"= 0x{val_b:02X} ({val_b})")
            if hasattr(self, 'value_label_r'):
                self.value_label_r.config(text=f"= 0x{val_r:02X} ({val_r})")

            if hasattr(self, 'gate_status_label'):
                self.gate_status_label.config(text=f"🟢 {operation}", bg="#0a0")

            if hasattr(self, 'gate_log'):
                self.gate_log.insert(tk.END, f"[{operation}] A=0x{val_a:02X} B=0x{val_b:02X} → R=0x{val_r:02X}\n")
                self.gate_log.see(tk.END)

            self.animate_gates_canvas(a_bits, b_bits, result_bits)

        except Exception:
            pass

    def animate_gates_canvas(self, a_bits, b_bits, result_bits):
        """Animate the full adder chain on the gates canvas"""
        try:
            if not hasattr(self, 'gates_canvas'):
                return

            canvas = self.gates_canvas
            canvas.delete("all")

            carry = [0] * 9
            for i in range(8):
                a = a_bits[i] if i < len(a_bits) else 0
                b = b_bits[i] if i < len(b_bits) else 0
                xor_ab = a ^ b
                carry[i+1] = (a & b) | (carry[i] & xor_ab)

            if hasattr(self, 'bit_labels_c'):
                for i in range(8):
                    idx = 7 - i
                    if i < len(self.bit_labels_c):
                        c_val = carry[idx+1] if idx+1 < len(carry) else 0
                        self.bit_labels_c[i].config(
                            text=str(c_val),
                            fg="#ff0" if c_val else "#333",
                            bg="#660" if c_val else "#333"
                        )

            if hasattr(self, 'carry_out_label'):
                self.carry_out_label.config(text=f"Cout: {carry[8]}")

            for i in range(8):
                x = 50 + i * 70
                y = 80

                a = a_bits[i] if i < len(a_bits) else 0
                b = b_bits[i] if i < len(b_bits) else 0
                r = result_bits[i] if i < len(result_bits) else 0
                c_in = carry[i]
                c_out = carry[i+1]

                active = (a or b or c_in)
                fill_color = "#4a6fa5" if active else "#2d4263"
                canvas.create_rectangle(x, y, x+50, y+80, fill=fill_color, outline="#00ff00", width=2)
                canvas.create_text(x+25, y+15, text=f"FA{i}", fill="#00ff00", font=("Courier", 9, "bold"))

                a_color = "#00ffff" if a else "#336"
                canvas.create_line(x+10, y-20, x+10, y, fill=a_color, width=3 if a else 1)
                canvas.create_text(x+10, y-25, text=str(a), fill=a_color, font=("Courier", 10, "bold"))

                b_color = "#00ff00" if b else "#363"
                canvas.create_line(x+25, y-20, x+25, y, fill=b_color, width=3 if b else 1)
                canvas.create_text(x+25, y-25, text=str(b), fill=b_color, font=("Courier", 10, "bold"))

                cin_color = "#ffff00" if c_in else "#663"
                if i > 0:
                    canvas.create_line(x-20, y+70, x, y+70, fill=cin_color, width=3 if c_in else 1, arrow=tk.LAST)
                else:
                    canvas.create_text(x-10, y+70, text=f"0", fill="#663", font=("Courier", 8))

                r_color = "#00ffff" if r else "#336"
                canvas.create_line(x+25, y+80, x+25, y+105, fill=r_color, width=3 if r else 1, arrow=tk.LAST)
                canvas.create_text(x+25, y+115, text=str(r), fill=r_color, font=("Courier", 10, "bold"))

                cout_color = "#ffff00" if c_out else "#663"
                canvas.create_line(x+50, y+70, x+70, y+70, fill=cout_color, width=3 if c_out else 1)

                xor_result = a ^ b
                and_result = a & b
                canvas.create_text(x+40, y+35, text=f"⊕{xor_result}", fill="#aaa", font=("Courier", 8))
                canvas.create_text(x+40, y+50, text=f"&{and_result}", fill="#aaa", font=("Courier", 8))

            canvas.create_text(300, 15, text="8-Bit Ripple Carry Adder - Live Data Flow",
                              fill="#ffffff", font=("Arial", 11, "bold"))

        except Exception:
            pass

    def update_alu_tab(self, val_a, val_b, result, operation):
        """Update the ALU & Control tab"""
        try:
            if hasattr(self, 'alu_op_label'):
                self.alu_op_label.config(text=f"Op: {operation}", bg="#4a6fa5")

            if hasattr(self, 'alu_canvas'):
                self.draw_alu_diagram(val_a, val_b, result, operation)

            if hasattr(self, 'micro_op_canvas'):
                self.draw_micro_op_pipeline()

            if hasattr(self, 'cu_canvas'):
                self.draw_cu_diagram(self.clock_phase % 5)

            signals = {
                'RegWrite': 1 if 'WRITE' in operation or 'STORE' in operation else 0,
                'MemRead': 1 if 'READ' in operation or 'LOAD' in operation or 'FETCH' in operation else 0,
                'MemWrite': 1 if 'WRITE' in operation or 'STORE' in operation else 0,
                'ALUOp': 1 if 'ALU' in operation or 'ADD' in operation else 0,
                'PCInc': 1,
                'BusEnable': 1
            }

            if hasattr(self, 'signal_labels'):
                for sig, val in signals.items():
                    if sig in self.signal_labels:
                        color = "#0f0" if val else "#f00"
                        self.signal_labels[sig].config(text=str(val), fg=color, bg="#030" if val else "#300")

        except Exception:
            pass

    def update_clock_tab(self, operation):
        """Update the Clock & Timing tab"""
        try:
            if hasattr(self, 'clock_canvas'):
                self.draw_clock_signal(self.cpu.cycles)

            active_signals = {}
            if 'READ' in operation or 'LOAD' in operation:
                active_signals['ADDR'] = True
                active_signals['DATA'] = True
                active_signals['MEM'] = True
            if 'ALU' in operation or 'ADD' in operation:
                active_signals['ALU'] = True

            if hasattr(self, 'timing_canvas'):
                self.draw_timing_diagram(active_signals)

            if hasattr(self, 'cycle_log'):
                self.cycle_log.insert(tk.END, f"[Cycle {self.cpu.cycles:03d}] {operation}\n")
                self.cycle_log.see(tk.END)

        except Exception:
            pass

    def pause_execution(self):
        """Pause execution"""
        self.is_running = False
        self.status_text.insert(tk.END, "\n⏸ Execution paused\n")

    def reset_all(self):
        """Reset CPU and memory"""
        self.cpu.reset()
        self.c_variables.clear()
        self.c_program_memory.clear()
        self.memory_allocations.clear()
        self.pointer_map = {}
        self.is_running = False
        self.clock_phase = 0
        self.status_text.delete("1.0", tk.END)
        self.status_text.insert(tk.END, "System reset. Ready to compile.\n")
        self.update_displays()

    def update_displays(self):
        """Update all visualization displays with enhanced activity highlighting"""
        state = self.cpu.get_cpu_state()

        for i in range(8):
            val = state['registers'][f'R{i}']
            reg_name = f"R{i} (SP)" if i == 7 else f"R{i}"
            self.reg_displays[i].config(text=f"0x{val:02X} ({val:3d})")
            if state.get('last_reg_accessed') == i:
                self.reg_displays[i].config(bg="#90EE90")
            else:
                self.reg_displays[i].config(bg="lightblue")

        db_info = state['data_bus']
        db_status = "🔴 ACTIVE" if db_info['source'] != "-" else "⚪ IDLE"
        self.databus_label.config(
            text=f"{db_status} | Value: 0x{db_info['value']:02X} | "
                 f"Source: {db_info['source']:8s} | Dest: {db_info['destination']:8s}",
            bg="#FFDD99" if db_info['source'] != "-" else "#FFFF99"
        )

        ab_info = state['address_bus']
        ab_status = "🔴 ACTIVE" if ab_info['source'] != "-" else "⚪ IDLE"
        self.addrbus_label.config(
            text=f"{ab_status} | Address: 0x{ab_info['address']:02X} | Source: {ab_info['source']:8s}",
            bg="#FFDD99" if ab_info['source'] != "-" else "#FFFF99"
        )

        self.pc_label.config(text=f"0x{state['pc']:02X}")
        self.ir_label.config(text=f"0x{state['ir']:02X}")
        self.cycles_label.config(text=f"{state['cycles']}")

        alu_active = state.get('alu_active', False)
        self.alu_result_label.config(
            text=f"0x{state['alu_result']:02X}",
            bg="#FFAAAA" if alu_active else "#FFCCCC"
        )
        flags = state['alu_flags']
        flags_str = f"[{flags.get('carry', 0)}:{flags.get('zero', 0)}:" \
                   f"{flags.get('overflow', 0)}:{flags.get('sign', 0)}]"
        self.flags_label.config(text=flags_str)

        self.update_memory_display(state)

    def update_memory_display(self, state):
        """Display memory and stack contents"""
        self.memory_display.delete("1.0", tk.END)

        sp_val = state['registers']['R7']

        self.memory_display.insert(tk.END, "MEMORY MAP:\n")
        self.memory_display.insert(tk.END, "=" * 70 + "\n")

        self.memory_display.insert(tk.END, "DATA REGION (0x00-0x7F):\n", "data_region")

        for mem_entry in state['memory_view'][:16]:
            addr = mem_entry['address']
            val = mem_entry['value']

            var_name = None
            for name, a in self.c_program_memory.items():
                if a == addr:
                    var_name = name
                    break

            if addr < 0x80:
                var_info = f" <-- {var_name}" if var_name else ""
                line = f"  [0x{addr:02X}] = 0x{val:02X} ({val:3d}){var_info}\n"
                self.memory_display.insert(tk.END, line, "data_region")

        self.memory_display.insert(tk.END, "\nSTACK REGION (0x80-0xFF):\n", "stack_region")
        self.memory_display.insert(tk.END, f"  Stack Pointer (R7): 0x{sp_val:02X}\n", "sp_pointer")

        for mem_entry in state['memory_view'][16:]:
            addr = mem_entry['address']
            val = mem_entry['value']
            if addr >= 0x80:
                line = f"  [0x{addr:02X}] = 0x{val:02X} ({val:3d})\n"
                tag = "sp_pointer" if addr == sp_val else "stack_region"
                self.memory_display.insert(tk.END, line, tag)

    def simulate_micro_op(self, phase, description, address):
        """Log and visualize a micro-operation"""
        self.current_micro_op = f"{phase}: {description}"

        if hasattr(self, 'gate_status_label'):
            colors = {"FETCH": "#e74c3c", "DECODE": "#f39c12", "EXECUTE": "#27ae60",
                     "MEMORY": "#3498db", "WRITEBACK": "#9b59b6"}
            self.gate_status_label.config(text=f"🔴 {phase}", bg=colors.get(phase, "gray"))

        if hasattr(self, 'alu_op_label'):
            self.alu_op_label.config(text=f"Phase: {phase}", bg="#ffdd99")

        if hasattr(self, 'gate_log'):
            timestamp = time.strftime("%H:%M:%S")
            self.gate_log.insert(tk.END, f"[{timestamp}] {phase}: {description}\n")
            self.gate_log.see(tk.END)

        if hasattr(self, 'cycle_log'):
            self.cycle_log.insert(tk.END, f"  → {phase}: {description}\n")
            self.cycle_log.see(tk.END)

        self.root.update()

    def update_bit_display(self, bits, target):
        """Update the bit-level display for input A, B, or result"""
        if target == 'a' and hasattr(self, 'bit_labels_a'):
            for i, lbl in enumerate(self.bit_labels_a):
                bit_val = bits[7-i] if (7-i) < len(bits) else 0
                lbl.config(text=str(bit_val), bg="#004400" if bit_val else "#333")
            value = sum(bits[i] * (2**i) for i in range(min(8, len(bits))))
            self.value_label_a.config(text=f"= 0x{value:02X} ({value})")

        elif target == 'b' and hasattr(self, 'bit_labels_b'):
            for i, lbl in enumerate(self.bit_labels_b):
                bit_val = bits[7-i] if (7-i) < len(bits) else 0
                lbl.config(text=str(bit_val), bg="#004400" if bit_val else "#333")
            value = sum(bits[i] * (2**i) for i in range(min(8, len(bits))))
            self.value_label_b.config(text=f"= 0x{value:02X} ({value})")

        elif target == 'r' and hasattr(self, 'bit_labels_r'):
            for i, lbl in enumerate(self.bit_labels_r):
                bit_val = bits[7-i] if (7-i) < len(bits) else 0
                lbl.config(text=str(bit_val), bg="#006666" if bit_val else "#333")
            value = sum(bits[i] * (2**i) for i in range(min(8, len(bits))))
            self.value_label_r.config(text=f"= 0x{value:02X} ({value})")

        self.root.update()

    def simulate_ripple_carry_addition(self, a_bits, b_bits):
        """Animate the ripple carry addition through full adders"""
        if not hasattr(self, 'bit_labels_c'):
            return

        carry = 0
        result_bits = []

        for i in range(8):
            a_bit = a_bits[i] if i < len(a_bits) else 0
            b_bit = b_bits[i] if i < len(b_bits) else 0

            xor_ab = a_bit ^ b_bit
            sum_bit = xor_ab ^ carry

            and_ab = a_bit & b_bit
            and_xor_c = xor_ab & carry
            new_carry = and_ab | and_xor_c

            result_bits.append(sum_bit)

            idx = 7 - i
            if idx >= 0 and idx < len(self.bit_labels_c):
                self.bit_labels_c[idx].config(text=str(carry), bg="#444400" if carry else "#333")

            if hasattr(self, 'gate_log'):
                self.gate_log.insert(tk.END,
                    f"  FA{i}: A={a_bit} B={b_bit} Cin={carry} → Sum={sum_bit} Cout={new_carry}\n")
                self.gate_log.see(tk.END)

            carry = new_carry

            if hasattr(self, 'bit_labels_r'):
                self.bit_labels_r[7-i].config(text=str(sum_bit), bg="#006666" if sum_bit else "#333")

            self.root.update()
            time.sleep(0.08)

        if hasattr(self, 'carry_out_label'):
            self.carry_out_label.config(text=f"Cout: {carry}", bg="#ffff00" if carry else "lightyellow")

        return result_bits, carry

    def update_all_visualizations(self, val_a, val_b, result, operation, active_signals):
        """Update all visualization tabs with current state"""
        if hasattr(self, 'alu_canvas'):
            self.draw_alu_diagram(val_a, val_b, result, operation)

        if hasattr(self, 'cu_canvas'):
            self.draw_cu_diagram(self.clock_phase)

        if hasattr(self, 'micro_op_canvas'):
            self.draw_micro_op_pipeline()

        if hasattr(self, 'clock_canvas'):
            self.draw_clock_signal(self.cpu.cycles)

        if hasattr(self, 'timing_canvas'):
            self.draw_timing_diagram(active_signals)

        if hasattr(self, 'signal_labels'):
            signal_map = {
                "RegWrite": operation in ["STORE", "DONE"],
                "MemRead": operation in ["LOAD_A", "LOAD_B"],
                "MemWrite": operation == "STORE",
                "ALUOp": operation == "ADD",
                "PCInc": operation == "DONE",
                "BusEnable": operation in ["LOAD_A", "LOAD_B", "STORE"]
            }
            for sig_name, lbl in self.signal_labels.items():
                is_active = signal_map.get(sig_name, False)
                lbl.config(text="1" if is_active else "0",
                          bg="#00ff00" if is_active else "#333",
                          fg="black" if is_active else "#f00")

        self.update_displays()
        self.root.update()

def main():
    root = tk.Tk()
    app = CPUVisualizer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
