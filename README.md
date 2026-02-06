
# 8-Bit CPU Simulator (8051-Inspired)

Have you ever wondered what happens inside a microcontroller when you call a function or add two numbers in C?

This simulator bridges the gap between high-level logic and hardware reality. By leveraging the GCC compiler to process actual C code and mapping the resulting execution to a simulated 8-bit environment, it allows students and engineers to see data moving between registers, memory, and the ALU.


##  Overview
This simulator bridges the gap between high-level programming and low-level hardware. By compiling C code using `gcc` and mapping it to a simulated 8-bit architecture, users can watch exactly how data moves through a computer in real-time.

> **Note:** Because the simulator relies on `gcc` for the heavy lifting of code analysis, having a working C compiler installed on your system is mandatory.

---

## Features
- **Live C Compilation:** Write C code and see it execute immediately.
- **Visual Data Flow:** Watch data move across the **Address Bus** and **Data Bus**.
- **Hardware Monitoring:** Real-time updates for:
    - **Registers (R0-R7):** Including Hex and Decimal values.
    - **ALU:** Visual feedback on arithmetic operations and status flags.
    - **Memory Map:** Dedicated sections for Data (0x00-0x7F) and the Stack (0x80-0xFF).
- **Execution Control:** Pause, reset, or step through cycles to inspect the CPU state.

---

## Installation

### Dependencies
You will need a C compiler (`gcc`) and Python's GUI toolkit (`tkinter`).

**For Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install gcc python3-tk build-essential

```

### Running the Simulator

1. Clone this repository:
```bash
git clone https://github.com/yourusername/CPU_Simulator.git

```

2. Navigate to the folder:
```bash
cd CPU_Simulator

```
3. Run the application:
```bash
python3 run.py

```
---

##  Open Source & Contributing

**This project is for the community!** 

This is an **Open Source** project designed to help students and developers learn how computers work under the hood.

* **Download & Use:** Anyone is free to download, use, and modify this project for learning or teaching.
* **Contribute:** If you have ideas for improvements, new features, or bug fixes, please submit a Pull Request!
* **Review:** I will review all contributions and merge updates that help improve the learning experience for everyone.

---

## Example Program

The simulator comes pre-loaded with an array addition script to demonstrate memory mapping:

```
#include <stdio.h>

int main() {
    int arrayA[5] = {10, 20, 30, 40, 50};
    int arrayB[5] = {5, 15, 25, 35, 45};
    int result[5];

    for(int i = 0; i < 5; i++) {
        result[i] = arrayA[i] + arrayB[i];
        printf("Index %d: Result %d\n", i, result[i]);
    }
    return 0;
}
```

### What to watch for during execution:

1. **Memory Allocation:** See `arrayA`, `arrayB`, and `result` get assigned to specific memory addresses.
2. **ALU Operations:** Watch the addition happen in the ALU before the value is stored back in memory.
3. **Bus Traffic:** Notice the address bus changing as it iterates through the loop.

---

## Troubleshooting

* **"gcc not found":** Run `sudo apt-get install build-essential`.
* **"tkinter not found":** Run `sudo apt-get install python3-tk`.
* **Compile Error:** Check the status area in the simulator for standard C syntax errors.

---