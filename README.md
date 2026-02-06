# 8-Bit CPU Simulator

A real-time CPU simulator that executes C programs with live visualization of all CPU operations.

## What It Does

This simulator compiles actual C programs using `gcc` and visualizes their execution on a simulated 8-bit CPU. You can write C code, compile it, and watch in real-time as:
- Variables are allocated to memory
- Registers update with values
- Data flows through buses
- ALU performs arithmetic operations
- Stack operations are tracked

## Installation

```bash
# Install dependencies
sudo apt-get install gcc python3-tk

# Run the simulator
cd path/CPU_Simulator
python3 run.py
```

## How to Use

1. Write or Edit C Code
   - Edit C program in the left panel
   - Or click "Load" to load a .c file

2. Click "Compile & Execute"
   - Compiles your C code with gcc
   - Executes it on the simulated CPU
   - Shows output in the status area

3. Watch the Visualization (Right Panel)
   - Registers: R0-R7 showing values in hex and decimal
   - Data Bus: Shows data transfers (value, source, destination)
   - Address Bus: Shows memory access patterns
   - Control Unit: Program counter, cycles executed
   - ALU Status: Computation results and flags
   - Memory: Data region (0x00-0x7F) and stack (0x80-0xFF)

4. Control Execution
   - Pause: Freeze execution to inspect state
   - Reset: Clear all state and start over

## Example Program

The simulator includes this sample array addition program:

```c
#include <stdio.h>

int main() {
    // Define two 8-bit-like arrays
    int arrayA[5] = {10, 20, 30, 40, 50};
    int arrayB[5] = {5, 15, 25, 35, 45};
    int result[5];

    printf("Performing Array Addition...\n");

    // Loop through the arrays and add elements
    for(int i = 0; i < 5; i++) {
        result[i] = arrayA[i] + arrayB[i];
        printf("Index %d: %d + %d = %d\n", i, arrayA[i], arrayB[i], result[i]);
    }

    return 0;
}
```

### What Happens When You Run It

1. Compilation: gcc compiles to executable
2. Memory Allocation: Variables allocated to addresses
   - arrayA: 0x00-0x04
   - arrayB: 0x05-0x09
   - result: 0x0A-0x0E

3. Execution: For each loop iteration:
   - Read arrayA[i] from memory (data bus shows transfer)
   - Read arrayB[i] from memory
   - ALU adds the two values
   - Write result to result[i]
   - All visualizations update in real-time

4. Output: Shows in status area
   ```
   Performing Array Addition...
   Index 0: 10 + 5 = 15
   Index 1: 20 + 15 = 35
   Index 2: 30 + 25 = 55
   Index 3: 40 + 35 = 75
   Index 4: 50 + 45 = 95
   ```

## Architecture

### CPU Components
- 8 Registers (R0-R7, R7 is Stack Pointer)
- 256 Bytes Memory (0x00-0x7F: data, 0x80-0xFF: stack)
- ALU with addition, subtraction, multiplication, division
- Control Unit with program counter and instruction decoding
- Data Bus (8-bit) for data transfers
- Address Bus (8-bit) for memory addressing

### Status Flags
- C (Carry): Set when arithmetic produces carry
- Z (Zero): Set when result is zero
- O (Overflow): Set when signed overflow occurs
- S (Sign): Set when result is negative

## Try It Out

```bash
# Start the simulator
python3 run.py

# What you'll see:
# 1. C code editor on the left
# 2. CPU visualization on the right
# 3. Sample array addition program already loaded

# Click " Compile & Execute"
# Watch the visualization show all CPU operations in real-time
```

## Write Your Own Program

```c
#include <stdio.h>

int main() {
    int x = 10;
    int y = 20;
    int z = x + y;
    
    printf("x + y = %d\n", z);
    
    return 0;
}
```

1. Paste your code into the editor
2. Click "Compile & Execute"
3. Watch the CPU execute it with live visualization

## Troubleshooting

"gcc not found"
```bash
sudo apt-get install build-essential
```

"tkinter not found"
```bash
sudo apt-get install python3-tk
```

Program won't compile
- Check C syntax (semicolons, braces, etc.)
- Try the built-in example first
- Error message appears in status area

