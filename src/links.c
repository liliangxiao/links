#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

#define MAX_STR 64
#define FILE_NAME "links_data.xml"

// --- Data Structures ---

typedef enum { DIR_NONE, DIR_IN, DIR_OUT } Direction;

typedef struct Port {
    char name[MAX_STR];
    char type[MAX_STR];
    Direction dir;
    char dest_module[MAX_STR]; 
    char dest_port[MAX_STR];
    struct Port* next;
} Port;

typedef struct Module {
    char name[MAX_STR];
    Port* ports;
    struct Module* next;
} Module;

Module* root_modules = NULL;

// --- Helper Functions ---

const char* dir_to_str(Direction d) {
    if (d == DIR_IN) return "in";
    if (d == DIR_OUT) return "out";
    return "none";
}

Direction str_to_dir(char* s) {
    if (strcmp(s, "in") == 0) return DIR_IN;
    if (strcmp(s, "out") == 0) return DIR_OUT;
    return DIR_NONE;
}

// Find or create a module
Module* get_module(const char* name, bool create) {
    if (!name || strlen(name) == 0) return NULL; // Safety check

    Module* cur = root_modules;
    Module* last = NULL;
    while (cur) {
        if (strcmp(cur->name, name) == 0) return cur;
        last = cur;
        cur = cur->next;
    }
    if (!create) return NULL;

    Module* new_mod = (Module*)malloc(sizeof(Module));
    if (!new_mod) { printf("Memory allocation failed\n"); exit(1); }
    
    strncpy(new_mod->name, name, MAX_STR - 1);
    new_mod->name[MAX_STR - 1] = '\0'; // Ensure null termination
    new_mod->ports = NULL;
    new_mod->next = NULL;

    if (last) last->next = new_mod;
    else root_modules = new_mod;
    return new_mod;
}

// Find or create a port
Port* get_port(Module* mod, const char* port_name, bool create) {
    if (!mod || !port_name || strlen(port_name) == 0) return NULL;

    Port* cur = mod->ports;
    Port* last = NULL;
    while (cur) {
        if (strcmp(cur->name, port_name) == 0) return cur;
        last = cur;
        cur = cur->next;
    }
    if (!create) return NULL;

    Port* new_port = (Port*)malloc(sizeof(Port));
    if (!new_port) { printf("Memory allocation failed\n"); exit(1); }

    strncpy(new_port->name, port_name, MAX_STR - 1);
    new_port->name[MAX_STR - 1] = '\0';
    
    strcpy(new_port->type, ""); // Default to empty
    strcpy(new_port->dest_module, "");
    strcpy(new_port->dest_port, "");
    new_port->dir = DIR_NONE;
    new_port->next = NULL;

    if (last) last->next = new_port;
    else mod->ports = new_port;
    return new_port;
}

// --- XML Persistence ---

void save_xml() {
    FILE* f = fopen(FILE_NAME, "w");
    if (!f) return;
    fprintf(f, "<root>\n");
    Module* m = root_modules;
    while (m) {
        fprintf(f, "  <module name=\"%s\">\n", m->name);
        Port* p = m->ports;
        while (p) {
            fprintf(f, "    <port name=\"%s\" type=\"%s\" dir=\"%s\" dest_mod=\"%s\" dest_port=\"%s\" />\n",
                    p->name, p->type, dir_to_str(p->dir), p->dest_module, p->dest_port);
            p = p->next;
        }
        fprintf(f, "  </module>\n");
        m = m->next;
    }
    fprintf(f, "</root>\n");
    fclose(f);
}

void load_xml() {
    FILE* f = fopen(FILE_NAME, "r");
    if (!f) return;
    
    char line[512];
    Module* current_mod = NULL;

    while (fgets(line, sizeof(line), f)) {
        if (strstr(line, "<module")) {
            char* name_start = strstr(line, "name=\"") + 6;
            char* name_end = strchr(name_start, '\"');
            if (name_end) {
                *name_end = '\0';
                current_mod = get_module(name_start, true);
            }
        } else if (strstr(line, "<port") && current_mod) {
            char name[MAX_STR], type[MAX_STR], dir_s[MAX_STR], dmod[MAX_STR], dport[MAX_STR];
            // Clear buffers first
            name[0] = 0; type[0] = 0; dir_s[0] = 0; dmod[0] = 0; dport[0] = 0;

            sscanf(line, "    <port name=\"%[^\"]\" type=\"%[^\"]\" dir=\"%[^\"]\" dest_mod=\"%[^\"]\" dest_port=\"%[^\"]\"", 
                   name, type, dir_s, dmod, dport);
            
            Port* p = get_port(current_mod, name, true);
            strncpy(p->type, type, MAX_STR - 1);
            p->dir = str_to_dir(dir_s);
            strncpy(p->dest_module, dmod, MAX_STR - 1);
            strncpy(p->dest_port, dport, MAX_STR - 1);
        }
    }
    fclose(f);
}

// --- Robust Parsing ---

// Parses "mod::port:type", "mod::port", or just "mod"
// Returns true if module name is found
bool parse_arg_safe(char* input, char* m_out, char* p_out, char* t_out) {
    // Clear outputs
    m_out[0] = '\0'; p_out[0] = '\0'; t_out[0] = '\0';

    if (!input || strlen(input) == 0) return false;

    // 1. Look for Double Colon (Module Separator)
    char* sep_mod = strstr(input, "::");
    
    if (sep_mod) {
        // We have "Module::Something"
        size_t m_len = sep_mod - input;
        if (m_len >= MAX_STR) m_len = MAX_STR - 1;
        strncpy(m_out, input, m_len);
        m_out[m_len] = '\0';

        char* rest = sep_mod + 2;
        
        // 2. Look for Single Colon (Type Separator) inside the 'Something'
        char* sep_type = strchr(rest, ':');
        
        if (sep_type) {
            // We have "Port:Type"
            size_t p_len = sep_type - rest;
            if (p_len >= MAX_STR) p_len = MAX_STR - 1;
            strncpy(p_out, rest, p_len);
            p_out[p_len] = '\0';

            strncpy(t_out, sep_type + 1, MAX_STR - 1);
            t_out[MAX_STR - 1] = '\0';
        } else {
            // We just have "Port"
            strncpy(p_out, rest, MAX_STR - 1);
            p_out[MAX_STR - 1] = '\0';
        }
    } else {
        // No "::" found. Treat the whole string as the Module Name.
        // Port and Type remain empty strings.
        strncpy(m_out, input, MAX_STR - 1);
        m_out[MAX_STR - 1] = '\0';
    }

    return (strlen(m_out) > 0);
}

// --- Commands ---

void print_usage() {
    printf("\n--- Link Manager CLI ---\n");
    printf("Manage connections between module ports.\n\n");
    printf("USAGE:\n");
    printf("  links <command> [arguments]\n\n");
    
    printf("COMMANDS:\n");
    printf("  add     <src> <dst>   Create a link from Source to Destination.\n");
    printf("                        Format:  Module::Port[:Type]\n");
    printf("                        Example: links add Sensor::Out:float Processor::In\n\n");

    printf("  remove  <src> <dst>   Remove an existing link.\n");
    printf("                        Example: links remove Sensor::Out Processor::In\n\n");
    
    printf("  edit    <mod::port> <type> <dir> Edit a port's type and direction (in|out|none).\n");
    printf("                        Example: links edit Sensor::Out int out\n\n"); // <-- NEW

    printf("  mvu     <mod::port>   Move a port up in the module's list (changes order in list/draw).\n"); // <-- NEW
    printf("                        Example: links mvu Sensor::PortB\n\n");

    printf("  mvd     <mod::port>   Move a port down in the module's list (changes order in list/draw).\n"); // <-- NEW

    printf("  list    <module>      List all ports and details for a specific module.\n");
    printf("                        Example: links list Sensor\n\n");

    printf("  draw                  Print a text-based hierarchy diagram to the console.\n\n");

    printf("  dot                   Generate 'graph.dot' and 'graph.svg' (requires Graphviz).\n\n");

    printf("  help                  Show this help message.\n");
    printf("\n");
}

void cmd_add(int argc, char* argv[]) {
    if (argc != 4) {
        printf("Error: 'add' requires source and destination.\nUsage: links add src_arg dst_arg\n");
        return;
    }

    char s_mod[MAX_STR], s_port[MAX_STR], s_type[MAX_STR];
    char d_mod[MAX_STR], d_port[MAX_STR], d_type[MAX_STR];

    // 1. Parse Input
    if (!parse_arg_safe(argv[2], s_mod, s_port, s_type)) {
        printf("Error: Invalid source format.\n"); return;
    }
    if (!parse_arg_safe(argv[3], d_mod, d_port, d_type)) {
        printf("Error: Invalid destination format.\n"); return;
    }

    // 2. Validate Source Requirements
    if (strlen(s_port) == 0) {
        printf("Error: Source must specify a port (e.g., Module::Port).\n");
        return;
    }
    // If source type is missing, set to default "unknown" if desired, or leave blank.
    if (strlen(s_type) == 0) strcpy(s_type, "unknown");

    // 3. Apply Defaults / Inheritance to Destination
    if (strlen(d_port) == 0) {
        strcpy(d_port, s_port); // Inherit port name
        printf("Info: Dest port not specified, using '%s'\n", d_port);
    }
    if (strlen(d_type) == 0) {
        strcpy(d_type, s_type); // Inherit type
    }

    // 4. Create/Link Objects
    Module* ms = get_module(s_mod, true);
    Port* ps = get_port(ms, s_port, true);
    strncpy(ps->type, s_type, MAX_STR-1);

    Module* md = get_module(d_mod, true);
    Port* pd = get_port(md, d_port, true);
    strncpy(pd->type, d_type, MAX_STR-1);

    // 5. Link
    ps->dir = DIR_OUT;
    strncpy(ps->dest_module, d_mod, MAX_STR-1);
    strncpy(ps->dest_port, d_port, MAX_STR-1);

    pd->dir = DIR_IN;
    // Clear dest info on IN port just in case
    pd->dest_module[0] = '\0';
    pd->dest_port[0] = '\0';

    printf("Linked: [%s::%s:%s] -> [%s::%s:%s]\n", 
           s_mod, s_port, s_type, d_mod, d_port, d_type);
}

void cmd_remove(int argc, char* argv[]) {
    if (argc != 4) {
        printf("Usage: links remove src_mod::src_port dst_mod::dst_port\n");
        return;
    }
    char s_mod[MAX_STR], s_port[MAX_STR], tmp[MAX_STR];
    char d_mod[MAX_STR], d_port[MAX_STR];

    parse_arg_safe(argv[2], s_mod, s_port, tmp);
    parse_arg_safe(argv[3], d_mod, d_port, tmp);

    Module* m = get_module(s_mod, false);
    if (!m) return;
    Port* p = get_port(m, s_port, false);
    if (!p) return;

    if (strcmp(p->dest_module, d_mod) == 0 && strcmp(p->dest_port, d_port) == 0) {
        p->dest_module[0] = '\0';
        p->dest_port[0] = '\0';
        p->dir = DIR_NONE;
        printf("Link removed.\n");
    } else {
        printf("Link not found.\n");
    }
}

// --- New Commands ---

// Helper function to find a port and its preceding port for list manipulation
Port* find_port_with_prev(Module* mod, const char* port_name, Port** prev_out) {
    *prev_out = NULL;
    if (!mod || !port_name || strlen(port_name) == 0) return NULL;

    Port* cur = mod->ports;
    Port* prev = NULL;
    while (cur) {
        if (strcmp(cur->name, port_name) == 0) {
            *prev_out = prev;
            return cur;
        }
        prev = cur;
        cur = cur->next;
    }
    return NULL;
}

void cmd_edit(int argc, char* argv[]) {
    if (argc != 5) {
        printf("Error: 'edit' requires module, port, and new type.\nUsage: links edit Module::Port NewType\n");
        return;
    }
    
    char m_name[MAX_STR], p_name[MAX_STR], tmp_type[MAX_STR];
    char* new_type = argv[3];
    char* new_dir_s = argv[4];

    if (!parse_arg_safe(argv[2], m_name, p_name, tmp_type)) {
        printf("Error: Invalid argument format for Module::Port.\n"); return;
    }

    if (strlen(p_name) == 0) {
        printf("Error: Must specify a port (e.g., Module::Port).\n"); return;
    }

    Module* m = get_module(m_name, false);
    if (!m) { printf("Error: Module '%s' not found.\n", m_name); return; }

    Port* p = get_port(m, p_name, false);
    if (!p) { printf("Error: Port '%s::%s' not found.\n", m_name, p_name); return; }

    // 1. Edit Type
    strncpy(p->type, new_type, MAX_STR - 1);
    p->type[MAX_STR - 1] = '\0';

    // 2. Edit Direction (and clear dest if setting to IN or NONE)
    Direction new_dir = str_to_dir(new_dir_s);
    if (new_dir == DIR_NONE || new_dir == DIR_IN) {
        p->dest_module[0] = '\0';
        p->dest_port[0] = '\0';
    }
    p->dir = new_dir;
    
    printf("Edited port [%s::%s]. New Type: %s, New Dir: %s\n", 
           m_name, p_name, p->type, dir_to_str(p->dir));
    printf("Note: To change destination for an 'out' port, use 'add' to relink.\n");
}


void cmd_move_port(int argc, char* argv[], bool move_up) {
    if (argc != 3) {
        printf("Error: '%s' requires a target port.\nUsage: links %s Module::Port\n", 
               move_up ? "mvu" : "mvd", move_up ? "mvu" : "mvd");
        return;
    }

    char m_name[MAX_STR], p_name[MAX_STR], tmp_type[MAX_STR];

    if (!parse_arg_safe(argv[2], m_name, p_name, tmp_type)) {
        printf("Error: Invalid argument format for Module::Port.\n"); return;
    }
    if (strlen(p_name) == 0) {
        printf("Error: Must specify a port (e.g., Module::Port).\n"); return;
    }

    Module* m = get_module(m_name, false);
    if (!m) { printf("Error: Module '%s' not found.\n", m_name); return; }

    Port* cur_port = NULL;
    Port* prev_port = NULL;
    
    // Find the current port and its predecessor
    cur_port = find_port_with_prev(m, p_name, &prev_port);
    if (!cur_port) { printf("Error: Port '%s::%s' not found.\n", m_name, p_name); return; }

    Port* target_port = NULL; // The port we are swapping with
    Port* target_prev = NULL; // The port before the target

    if (move_up) {
        // Find the port *before* prev_port. We need to swap prev_port and cur_port.
        if (!prev_port) {
            printf("Error: Port '%s::%s' is already the first port (cannot move up).\n", m_name, p_name);
            return;
        }
        
        target_port = prev_port;
        
        // Find the port before target_port (i.e., the port two steps before cur_port)
        if (m->ports == target_port) {
            target_prev = NULL; // Target is the first port
        } else {
            Port* finder = m->ports;
            while (finder && finder->next != target_port) {
                finder = finder->next;
            }
            target_prev = finder;
        }

    } else { // move_down
        // Find the port *after* cur_port. We need to swap cur_port and next_port.
        target_port = cur_port->next;
        if (!target_port) {
            printf("Error: Port '%s::%s' is already the last port (cannot move down).\n", m_name, p_name);
            return;
        }
        target_prev = cur_port;
    }

    // --- Perform Swap of target_port and cur_port in the list ---
    // 1. target_prev (or module->ports) must point to cur_port.
    if (target_prev) {
        target_prev->next = cur_port;
    } else {
        m->ports = cur_port;
    }

    // 2. target_port must point to cur_port's original next (which is now target_port's next).
    target_port->next = cur_port->next;

    // 3. cur_port must point to target_port.
    cur_port->next = target_port;
    
    printf("Moved port '%s::%s' %s.\n", m_name, p_name, move_up ? "up" : "down");
}

// Wrapper for cmd_move_port(..., true)
void cmd_move_port_up(int argc, char* argv[]) {
    cmd_move_port(argc, argv, true);
}

// Wrapper for cmd_move_port(..., false)
void cmd_move_port_down(int argc, char* argv[]) {
    cmd_move_port(argc, argv, false);
}

void cmd_list(const char* mod_name) {
    Module* m = get_module(mod_name, false);
    if (!m) { printf("Module not found.\n"); return; }
    
    printf("Module: %s\n", m->name);
    printf("----------------------------------------------------\n");
    printf("%-15s | %-10s | %-5s | %s\n", "Port", "Type", "Dir", "Destination");
    printf("----------------------------------------------------\n");
    
    Port* p = m->ports;
    while (p) {
        char dest[150];
        if (p->dir == DIR_OUT && strlen(p->dest_module) > 0) 
            snprintf(dest, sizeof(dest), "%s::%s", p->dest_module, p->dest_port);
        else 
            strcpy(dest, "--");

        printf("%-15s | %-10s | %-5s | %s\n", p->name, p->type, dir_to_str(p->dir), dest);
        p = p->next;
    }
}

void cmd_draw() {
    printf("\n--- System Diagram ---\n");
    Module* m = root_modules;
    while (m) {
        printf("[%s]\n", m->name);
        Port* p = m->ports;
        while(p) {
            if (p->dir == DIR_IN)
                printf("  -> (IN)  %s (%s)\n", p->name, p->type);
            else if (p->dir == DIR_OUT)
                printf("  <- (OUT) %s (%s) -> [%s::%s]\n", 
                       p->name, p->type, p->dest_module, p->dest_port);
            p = p->next;
        }
        m = m->next;
    }
}

void cmd_dot() {
    FILE* f = fopen("graph.dot", "w");
    if (!f) return;

    fprintf(f, "digraph G {\n");
    fprintf(f, "  rankdir=LR;\n");
    
    // Use polyline to prevent wires from 'floating' or missing ports
    fprintf(f, "  splines=polyline;\n");
    
    fprintf(f, "  nodesep=0.8;\n"); 
    fprintf(f, "  ranksep=1.0;\n");
    
    // Default formatting for standard nodes
    fprintf(f, "  node [shape=plain, fontname=\"Arial\", fontsize=12];\n");
    fprintf(f, "  edge [fontname=\"Arial\", fontsize=10];\n\n");
    
    Module* m = root_modules;
    while (m) {
        fprintf(f, "  %s [label=<\n", m->name);
        
        // --- OUTER TABLE (Structure Only) ---
        // border=0 ensures no outer frame.
        fprintf(f, "   <table border=\"0\" cellborder=\"0\" cellspacing=\"0\" cellpadding=\"0\">\n");
        fprintf(f, "    <tr>\n");

        // --- 1. LEFT COLUMN: INPUTS ---
        fprintf(f, "      <td>\n"); 
        
        bool has_in = false;
        Port* p = m->ports;
        while(p) { if(p->dir == DIR_IN) has_in = true; p = p->next; }

        if (has_in) {
            // Inner table: Handles the border and white background
            fprintf(f, "        <table border=\"0\" cellborder=\"1\" cellspacing=\"0\" cellpadding=\"4\" bgcolor=\"#ffffff\">\n");
            p = m->ports;
            while(p) {
                if(p->dir == DIR_IN) {
                    fprintf(f, "          <tr><td port=\"%s\">%s</td></tr>\n", p->name, p->name);
                }
                p = p->next;
            }
            fprintf(f, "        </table>\n");
        }
        fprintf(f, "      </td>\n");

        // --- 2. MIDDLE COLUMN: MODULE NAME ---
        // FIX: Moved border/bgcolor from <TD> to the <TABLE>. 
        // This fixes the "mismatched tag" error on older/strict parsers.
        fprintf(f, "      <td>\n");
        fprintf(f, "        <table border=\"1\" cellborder=\"0\" cellspacing=\"0\" cellpadding=\"8\" bgcolor=\"#f0f0f0\">\n");
        fprintf(f, "          <tr><td><b>%s</b></td></tr>\n", m->name);
        fprintf(f, "        </table>\n");
        fprintf(f, "      </td>\n");

        // --- 3. RIGHT COLUMN: OUTPUTS ---
        fprintf(f, "      <td>\n");
        
        bool has_out = false;
        p = m->ports;
        while(p) { if(p->dir == DIR_OUT) has_out = true; p = p->next; }

        if (has_out) {
            // Inner table: Handles the border and white background
            fprintf(f, "        <table border=\"0\" cellborder=\"1\" cellspacing=\"0\" cellpadding=\"4\" bgcolor=\"#ffffff\">\n");
            p = m->ports;
            while(p) {
                if(p->dir == DIR_OUT) {
                    fprintf(f, "          <tr><td port=\"%s\">%s</td></tr>\n", p->name, p->name);
                }
                p = p->next;
            }
            fprintf(f, "        </table>\n");
        }
        fprintf(f, "      </td>\n");

        fprintf(f, "    </tr>\n");
        fprintf(f, "   </table>>];\n\n");

        m = m->next;
    }

    fprintf(f, "\n");
    
    // --- Define Edges ---
    m = root_modules;
    while (m) {
        Port* p = m->ports;
        while (p) {
            if (p->dir == DIR_OUT && strlen(p->dest_module) > 0) {
                // Removed :e/:w constraints to allow polyline splines to route cleanly
                fprintf(f, "  %s:%s -> %s:%s;\n", 
                        m->name, p->name, p->dest_module, p->dest_port);
            }
            p = p->next;
        }
        m = m->next;
    }

    fprintf(f, "}\n");
    fclose(f);
    
    system("dot -Tsvg graph.dot -o graph.svg");
    system("dot -Tpng graph.dot -o graph.png");
    printf("Generated graph.svg successfully.\n");
}

int main(int argc, char* argv[]) {
    // If no arguments or user asks for help
    if (argc < 2 || strcmp(argv[1], "help") == 0 || strcmp(argv[1], "-h") == 0) {
        print_usage();
        return 0;
    }

    load_xml();

    if (strcmp(argv[1], "add") == 0) cmd_add(argc, argv);
    else if (strcmp(argv[1], "edit") == 0 || strcmp(argv[1], "ed") == 0) cmd_edit(argc, argv); // <-- NEW
    else if (strcmp(argv[1], "mvu") == 0) cmd_move_port_up(argc, argv); // <-- NEW
    else if (strcmp(argv[1], "mvd") == 0) cmd_move_port_down(argc, argv); // <-- NEW
    else if (strcmp(argv[1], "list") == 0 && argc > 2) cmd_list(argv[2]);
    else if (strcmp(argv[1], "remove") == 0) cmd_remove(argc, argv);
    else if (strcmp(argv[1], "draw") == 0) cmd_draw();
    else if (strcmp(argv[1], "dot") == 0) cmd_dot();
    else {
        printf("Unknown command: %s\n", argv[1]);
        print_usage();
    }
    
    save_xml();
    return 0;
}