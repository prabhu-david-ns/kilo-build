CC      := gcc
CFLAGS  := -std=c11 -Wall -Wextra -g
TARGET  := tedit

$(TARGET): tedit.c
	$(CC) $(CFLAGS) -o $(TARGET) tedit.c

# spec 04 research-derived rebuild — kept alongside the spec 05 prep-only
# version as its own tree (landed 2026-09-06 merge of impl/04).
tedit-research: tedit-research/tedit.c
	$(CC) $(CFLAGS) -o tedit-research/tedit tedit-research/tedit.c

clean:
	rm -f $(TARGET) tedit-research/tedit

.PHONY: clean tedit-research
