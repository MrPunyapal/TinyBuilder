/* Packaging test double only: this is NOT llama.cpp and cannot infer. */
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc == 2 && (strcmp(argv[1], "--version") == 0 ||
                      strcmp(argv[1], "--help") == 0)) {
        puts("TINYBUILDER_PACKAGING_FIXTURE_NOT_LLAMA_CPP");
        return 0;
    }
    fputs("Fixture cannot perform inference.\n", stderr);
    return 2;
}
