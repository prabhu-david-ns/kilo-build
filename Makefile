# tedit — dependency-free VT100 terminal editor in C (spec 04).
# gcc only, against libc/POSIX. No build-system dependencies.

CC      ?= gcc
CFLAGS  ?= -std=c11 -Wall -Wextra -O2 -g

tedit: tedit.c
	$(CC) $(CFLAGS) -o $@ tedit.c

clean:
	rm -f tedit

.PHONY: clean