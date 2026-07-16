"""Regression: the app must work under Finder's minimal PATH.

Apps launched from Finder get PATH=/usr/bin:/bin:/usr/sbin:/sbin — without
/opt/homebrew/bin. Tool paths must therefore be resolved to absolute paths
at import time, not left to subprocess PATH lookup.
"""
import os
import subprocess
import sys

import pytest


def test_tool_paths_are_absolute_when_installed():
    from anamnese import config
    for tool in (config.FFMPEG_BIN, config.WHISPER_BIN, config.OLLAMA_BIN):
        # resolved on any machine where install.sh has run; on a bare CI
        # machine the fallback (bare name) is allowed
        if "/" in tool:
            assert os.path.isabs(tool) and os.path.exists(tool)


@pytest.mark.skipif(not os.path.exists("/opt/homebrew/bin/ffmpeg"),
                    reason="Homebrew ffmpeg required")
def test_tools_resolve_under_finder_minimal_path():
    code = ("from anamnese import config; "
            "assert config.FFMPEG_BIN.startswith('/'), config.FFMPEG_BIN; "
            "assert config.WHISPER_BIN.startswith('/'), config.WHISPER_BIN; "
            "print('resolved')")
    env = dict(os.environ, PATH="/usr/bin:/bin:/usr/sbin:/sbin")
    r = subprocess.run([sys.executable, "-c", code], env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "resolved" in r.stdout
