#include <stdio.h>
#include <gem5/m5ops.h>

int main()
{
    size_t vlen = 0;
    
    m5_work_begin(12, 0);
    asm volatile(
            "incb %[vlen]\n\t"
            "ptrue p0.d\n\t"
            "fmla z0.d, p0/m, z1.d, z2.d\n\t"
            : [vlen] "=r" (vlen)
            :
            : "z0", "z1", "z2"
            );
    m5_work_end(12, 0);

    printf("Hello, vector length is %zu\n", vlen);

    m5_exit(0);
    return 0;
}
