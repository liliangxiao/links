CC = gcc
CFLAGS = -Wall -Wextra -std=c11

all: links graph

links: src/links.c
	$(CC) $(CFLAGS) src/links.c -o src/links

clean:
	rm -f src/links src/*.png src/*.svg
