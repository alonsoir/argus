#pragma once
// safe_exec.hpp — Primitivos de ejecución sin shell (CWE-78)
// Consejo 8/8 DAY 128: execve() sin shell es el único mecanismo correcto.
// NEVER system() / popen() con strings concatenados.
//
// Funciones:
//   validate_chain_name()       — allowlist iptables chain names
//   validate_table_name()       — allowlist de tablas iptables válidas
//   safe_exec()                 — fork+execv sin captura de output
//   safe_exec_with_output()     — fork+execv+pipe, captura stdout+stderr
//   safe_exec_with_file_out()   — fork+execv, stdout→fichero (para iptables-save)
//   safe_exec_with_file_in()    — fork+execv, stdin←fichero (para iptables-restore)

#include <string>
#include <vector>
#include <regex>
#include <unordered_set>
#include <sstream>
#include <stdexcept>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <fcntl.h>
#include <cstring>

// ---------------------------------------------------------------------------
// Validadores — allowlist estricta
// ---------------------------------------------------------------------------

/// Valida chain name: solo [A-Za-z0-9_-], 1..29 caracteres (límite iptables).
/// Rechaza cualquier metacaracter shell: ; | & > < ` $ ( ) { } * ? !
inline bool validate_chain_name(const std::string& name) {
    if (name.empty() || name.size() > 29) return false;
    // Null byte check: std::regex_match trunca en \0, hay que rechazarlo explicitamente
    if (name.find('\0') != std::string::npos) return false;
    static const std::regex allowed("^[A-Za-z0-9_-]+$");
    return std::regex_match(name, allowed);
}

/// Valida tabla iptables contra conjunto fijo de valores conocidos.
inline bool validate_table_name(const std::string& name) {
    static const std::unordered_set<std::string> valid{
        "filter", "nat", "mangle", "raw", "security"
    };
    return valid.count(name) > 0;
}

/// Valida ruta de fichero: no permite .. ni caracteres de shell.
/// Debe ser ruta absoluta o relativa simple sin metacaracteres.
inline bool validate_filepath(const std::string& path) {
    if (path.empty() || path.size() > 4096) return false;
    // Rechazar path traversal y metacaracteres shell
    static const std::regex allowed("^[A-Za-z0-9_.\\-/]+$");
    if (!std::regex_match(path, allowed)) return false;
    // Rechazar path traversal
    if (path.find("..") != std::string::npos) return false;
    return true;
}

// ---------------------------------------------------------------------------
// is_safe_for_exec — defensa en profundidad contra null bytes (Consejo 8/8 DAY 129)
// strlen() se detiene en el primer \0. Si arg.size() != strlen(arg.c_str())
// hay un \0 interno — fail-closed, nunca truncar silenciosamente en execv().
// ---------------------------------------------------------------------------
[[nodiscard]] inline bool is_safe_for_exec(const std::string& arg) noexcept {
    return arg.size() == std::strlen(arg.c_str());
}

// ---------------------------------------------------------------------------
// safe_exec — fork+execv sin shell, sin captura de output
// Redirige stdout+stderr a /dev/null.
// Retorna exit code del proceso hijo, o -1 si fork/execv falla.
// ---------------------------------------------------------------------------
inline int safe_exec(const std::vector<std::string>& args) {
    if (args.empty()) return -1;
    // Defensa en profundidad: null byte en argv[i] trunca arg silenciosamente (Consejo 8/8 DAY 129)
    for (const auto& a : args) {
        if (!is_safe_for_exec(a)) return -1;
    }

    pid_t pid = fork();
    if (pid == -1) return -1;

    if (pid == 0) {
        // Hijo: redirigir stdout+stderr a /dev/null
        int devnull = open("/dev/null", O_WRONLY);
        if (devnull != -1) {
            dup2(devnull, STDOUT_FILENO);
            dup2(devnull, STDERR_FILENO);
            close(devnull);
        }
        std::vector<const char*> argv;
        argv.reserve(args.size() + 1);
        for (const auto& a : args) argv.push_back(a.c_str());
        argv.push_back(nullptr);
        execv(args[0].c_str(), const_cast<char* const*>(argv.data()));
        _exit(127); // execv falló
    }

    // Padre
    int status = 0;
    waitpid(pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

// ---------------------------------------------------------------------------
// safe_exec_with_output — fork+execv+pipe, captura stdout+stderr
// Retorna {exit_code, output_string}
// ---------------------------------------------------------------------------
inline std::pair<int, std::string> safe_exec_with_output(
    const std::vector<std::string>& args)
{
    if (args.empty()) return {-1, "empty args"};
    // Defensa en profundidad: null byte check (Consejo 8/8 DAY 129)
    for (const auto& a : args) {
        if (!is_safe_for_exec(a)) return {-1, "null byte in argument"};
    }

    int pipefd[2];
    if (pipe(pipefd) == -1) return {-1, "pipe() failed"};

    pid_t pid = fork();
    if (pid == -1) {
        close(pipefd[0]);
        close(pipefd[1]);
        return {-1, "fork() failed"};
    }

    if (pid == 0) {
        // Hijo: escribir en extremo write del pipe
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[1]);

        std::vector<const char*> argv;
        argv.reserve(args.size() + 1);
        for (const auto& a : args) argv.push_back(a.c_str());
        argv.push_back(nullptr);
        execv(args[0].c_str(), const_cast<char* const*>(argv.data()));
        _exit(127);
    }

    // Padre: leer desde extremo read
    close(pipefd[1]);
    std::string output;
    {
        char buf[4096];
        ssize_t n;
        while ((n = read(pipefd[0], buf, sizeof(buf))) > 0) {
            output.append(buf, static_cast<size_t>(n));
        }
    }
    close(pipefd[0]);

    int status = 0;
    waitpid(pid, &status, 0);
    return {WIFEXITED(status) ? WEXITSTATUS(status) : -1, output};
}

// ---------------------------------------------------------------------------
// safe_exec_with_file_out — iptables-save: stdout → fichero
// Equivalente a: execv args > filepath  (sin shell)
// ---------------------------------------------------------------------------
inline int safe_exec_with_file_out(
    const std::vector<std::string>& args,
    const std::string& filepath)
{
    if (args.empty()) return -1;
    // Defensa en profundidad: null byte check (Consejo 8/8 DAY 129)
    for (const auto& a : args) {
        if (!is_safe_for_exec(a)) return -1;
    }

    pid_t pid = fork();
    if (pid == -1) return -1;

    if (pid == 0) {
        int fd = open(filepath.c_str(),
                      O_WRONLY | O_CREAT | O_TRUNC,
                      static_cast<mode_t>(0600));
        if (fd == -1) _exit(1);
        dup2(fd, STDOUT_FILENO);
        // stderr a /dev/null para no contaminar el fichero
        int devnull = open("/dev/null", O_WRONLY);
        if (devnull != -1) { dup2(devnull, STDERR_FILENO); close(devnull); }
        close(fd);

        std::vector<const char*> argv;
        argv.reserve(args.size() + 1);
        for (const auto& a : args) argv.push_back(a.c_str());
        argv.push_back(nullptr);
        execv(args[0].c_str(), const_cast<char* const*>(argv.data()));
        _exit(127);
    }

    int status = 0;
    waitpid(pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

// ---------------------------------------------------------------------------
// safe_exec_with_file_in — iptables-restore: stdin ← fichero
// Equivalente a: execv args < filepath  (sin shell)
// ---------------------------------------------------------------------------
inline int safe_exec_with_file_in(
    const std::vector<std::string>& args,
    const std::string& filepath)
{
    if (args.empty()) return -1;
    // Defensa en profundidad: null byte check (Consejo 8/8 DAY 129)
    for (const auto& a : args) {
        if (!is_safe_for_exec(a)) return -1;
    }

    pid_t pid = fork();
    if (pid == -1) return -1;

    if (pid == 0) {
        int fd = open(filepath.c_str(), O_RDONLY);
        if (fd == -1) _exit(1);
        dup2(fd, STDIN_FILENO);
        close(fd);

        std::vector<const char*> argv;
        argv.reserve(args.size() + 1);
        for (const auto& a : args) argv.push_back(a.c_str());
        argv.push_back(nullptr);
        execv(args[0].c_str(), const_cast<char* const*>(argv.data()));
        _exit(127);
    }

    int status = 0;
    waitpid(pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}
