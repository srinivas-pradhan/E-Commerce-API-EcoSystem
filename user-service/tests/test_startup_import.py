import subprocess
import sys
import unittest
from pathlib import Path


class StartupImportTest(unittest.TestCase):
    def test_start_script_exports_local_env_file(self):
        service_dir = Path(__file__).resolve().parents[1]
        start_script = service_dir / "start-user-service.sh"

        script = start_script.read_text()

        self.assertIn("source .env", script)
        self.assertIn("set -a", script)
        self.assertIn("set +a", script)

    def test_main_imports_when_loaded_from_repo_root(self):
        service_dir = Path(__file__).resolve().parents[1]
        repo_root = service_dir.parent
        code = (
            "import importlib.util; "
            "spec = importlib.util.spec_from_file_location('user_service_main', 'user-service/main.py'); "
            "module = importlib.util.module_from_spec(spec); "
            "spec.loader.exec_module(module); "
            "print(module.app.title)"
        )

        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout.strip(), "User Auth Service")
