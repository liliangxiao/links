BUILD_DIR = build
LINKS_TOOL=./links
CC = gcc
CFLAGS = -Wall -Wextra -std=c11

.PHONY: all links gui graph clean build_dir setup_build

all: setup_build $(BUILD_DIR)/links $(BUILD_DIR)/gui.py $(BUILD_DIR)/links_data.xml $(BUILD_DIR)/vehicle_architecture_example.sh graph

setup_build:
	@mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/links: src/links.c
	$(CC) $(CFLAGS) $< -o $@

$(BUILD_DIR)/gui.py: src/gui.py
	cp $< $@

$(BUILD_DIR)/links_data.xml: src/links_data.xml
	@if [ -f "$<" ]; then cp $< $@; else touch $@; fi

$(BUILD_DIR)/vehicle_architecture_example.sh: src/vehicle_architecture_example.sh
	cp $< $@
	chmod +x $@

graph: $(BUILD_DIR)/links $(BUILD_DIR)/links_data.xml # Ensure links executable and data are present
	@# Generate graph using the executable in build directory, outputting to build directory
	@# The links tool command 'dot' will create files in its current working directory.
	@# We run it from $(BUILD_DIR) so the files are created there.
	cd $(BUILD_DIR) && $(LINKS_TOOL) dot
	@echo "Graph files generated in $(BUILD_DIR)/"

gui: $(BUILD_DIR)/gui.py
	cd ./buid && python3 $(BUILD_DIR)/gui.py

clean:
	rm -rf $(BUILD_DIR)
