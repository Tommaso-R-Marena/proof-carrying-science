/* Research IO entry point. Same runtime protocol as Lean's generated main.
   This adapter and the native compiler/runtime remain trusted host code. */
#include <lean/lean.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <arpa/inet.h>
extern lean_object *initialize_Bridge(uint8_t);
extern lean_object *pgsi_research_main(lean_object *);
extern char **lean_setup_args(int, char **);
extern void lean_initialize(void);
int main(int argc, char **argv) {
    /* Runtime diagnostic only, never a semantic Lean authorization verdict. */
    if (argc == 4 && strcmp(argv[1], "isolation") == 0) {
        char ns[128] = {0};
        ssize_t n = readlink("/proc/self/ns/net", ns, sizeof(ns) - 1);
        if (n < 0) return 3;
        ns[n] = 0;
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        struct sockaddr_in address = {0};
        address.sin_family = AF_INET;
        address.sin_port = htons((uint16_t)atoi(argv[3]));
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        int connected = fd >= 0 && connect(fd, (struct sockaddr *)&address, sizeof(address)) == 0;
        if (fd >= 0) close(fd);
        int writable = open("/authority", O_WRONLY);
        int wrote = writable >= 0;
        if (writable >= 0) close(writable);
        printf("{\"host_path_visible\":%s,\"parent_secret_visible\":%s,\"host_loopback_connected\":%s,\"authority_writable\":%s,\"net_namespace\":\"%s\"}\n",
            access(argv[2], F_OK) == 0 ? "true" : "false",
            getenv("PCS_PGSI_TEST_SECRET") ? "true" : "false",
            connected ? "true" : "false", wrote ? "true" : "false", ns);
        return 0;
    }
    argv = lean_setup_args(argc, argv);
    lean_initialize();
    lean_set_panic_messages(false);
    lean_object *result = initialize_Bridge(1);
    lean_set_panic_messages(true);
    lean_io_mark_end_initialization();
    if (lean_io_result_is_ok(result)) {
        lean_dec_ref(result);
        lean_init_task_manager();
        lean_object *args = lean_box(0);
        for (int i = argc - 1; i > 0; --i) {
            lean_object *node = lean_alloc_ctor(1, 2, 0);
            lean_ctor_set(node, 0, lean_mk_string(argv[i]));
            lean_ctor_set(node, 1, args);
            args = node;
        }
        result = pgsi_research_main(args);
    }
    lean_finalize_task_manager();
    if (!lean_io_result_is_ok(result)) {
        lean_io_result_show_error(result);
        lean_dec_ref(result);
        return 2;
    }
    int code = lean_unbox_uint32(lean_io_result_get_value(result));
    lean_dec_ref(result);
    return code;
}
