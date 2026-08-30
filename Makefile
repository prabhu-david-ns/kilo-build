CC      := gcc
CFLAGS  := -std=c11 -Wall -Wextra -g
TARGET  := tedit

$(TARGET): tedit.c
	$(CC) $(CFLAGS) -o $(TARGET) tedit.c

clean:
	rm -f $(TARGET)

.PHONY: clean