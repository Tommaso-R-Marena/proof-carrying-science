CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Wpedantic -Wconversion -Werror

all: libpcs_srcbind.so

pcs_srcbind.o: pcs_srcbind.c pcs_srcbind.h
	$(CC) $(CFLAGS) -fPIC -c pcs_srcbind.c -o pcs_srcbind.o

libpcs_srcbind.so: pcs_srcbind.o
	$(CC) -shared -o libpcs_srcbind.so pcs_srcbind.o

clean:
	rm -f pcs_srcbind.o libpcs_srcbind.so

.PHONY: all clean
