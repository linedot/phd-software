#include <stdio.h>

int main()
{
    size_t vlen = 0;
    asm volatile(
            "vsetvli %[vlen], zero, e32, m1, ta, ma\n\t"
            : [vlen] "=r" (vlen)
            :
            :
            );

    printf("Hello, VLEN is %zu\n", vlen);
    return 0;
}
