/* Audiomnesis app-bundle launcher.
 *
 * A compiled Mach-O executable (rather than a shell script) is required for
 * macOS TCC to attribute file/microphone permissions to the app bundle and
 * show its permission prompts. Compiled and signed by install.sh:
 *   clang -O2 -o Audiomnesis.app/Contents/MacOS/Audiomnesis app_src/launcher.c
 *   codesign --force --deep -s - Audiomnesis.app
 *
 * The bundle must stay inside the project folder: it launches the project's
 * virtualenv python on app.py, with stdout/stderr appended to .app.log.
 */
#include <limits.h>
#include <libgen.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void) {
    char exe[PATH_MAX];
    uint32_t size = sizeof(exe);
    if (_NSGetExecutablePath(exe, &size) != 0)
        return 1;
    char real[PATH_MAX];
    if (realpath(exe, real) == NULL)
        return 1;

    /* real = <root>/Audiomnesis.app/Contents/MacOS/Audiomnesis */
    char *macos_dir = dirname(real);
    char up[PATH_MAX], root[PATH_MAX];
    snprintf(up, sizeof up, "%s/../../..", macos_dir);
    if (realpath(up, root) == NULL)
        return 1;

    char py[PATH_MAX];
    snprintf(py, sizeof py, "%s/.venv/bin/python", root);
    if (access(py, X_OK) != 0) {
        system("osascript -e 'display alert \"Audiomnesis — installation requise\" "
               "message \"L environnement n est pas installé. Ouvrez le Terminal "
               "dans le dossier du projet et lancez :\\n\\n./install.sh\" as critical'");
        return 1;
    }

    if (chdir(root) != 0)
        return 1;
    setenv("OLLAMA_FLASH_ATTENTION", "1", 1);
    setenv("OLLAMA_KV_CACHE_TYPE", "q8_0", 1);

    char logpath[PATH_MAX];
    snprintf(logpath, sizeof logpath, "%s/.app.log", root);
    freopen(logpath, "a", stdout);
    freopen(logpath, "a", stderr);

    execl(py, py, "app.py", (char *)NULL);
    perror("exec python failed");
    return 1;
}
