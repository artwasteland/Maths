/* Keep msolve's randomized separator reproducible without changing its solver.
 * Build with gcc -c, then ld -shared as separate commands (two-process ceiling).
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <unistd.h>
void srand(unsigned int ignored) {
    (void)ignored;
    void (*original)(unsigned int) = dlsym(RTLD_NEXT, "srand");
    const char *value = getenv("GP10_MSOLVE_SEED");
    if (!original || !value) _exit(125);
    original((unsigned int)strtoul(value, 0, 10));
}
__attribute__((constructor)) static void seed_initial_state(void) { srand(0); }
