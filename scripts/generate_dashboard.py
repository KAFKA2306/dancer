import subprocess
import html
from pathlib import Path

def main() -> int:
    result = subprocess.run(["pytest", "-q"], capture_output=True, text=True)
    output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    dashboard_dir = Path("dashboard")
    dashboard_dir.mkdir(exist_ok=True)
    with open(dashboard_dir / "index.html", "w", encoding="utf-8") as fh:
        fh.write("<html><body><h1>Test Results</h1><pre>")
        fh.write(html.escape(output))
        fh.write("</pre></body></html>")
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
