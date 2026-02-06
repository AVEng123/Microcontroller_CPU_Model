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
