import json
import subprocess
import sys
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path


class HttpTests(unittest.TestCase):
    def test_server_routes_auth_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "cryptolab.server",
                    "--port",
                    "0",
                    "--db",
                    str(Path(directory) / "runs.db"),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                url = process.stdout.readline().strip().split()[-1]
                self.assertTrue(url.startswith("http://127.0.0.1:"))
                with urllib.request.urlopen(url) as response:
                    self.assertIn(b"Input workspace", response.read())
                    self.assertEqual(response.headers["X-Frame-Options"], "DENY")
                with urllib.request.urlopen(url + "/api/bootstrap") as response:
                    boot = json.load(response)
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(url + "/api/runs")
                self.assertEqual(context.exception.code, 403)
                headers = {
                    "X-Session-Token": boot["token"],
                    "Content-Type": "application/json",
                }

                def post(route, payload):
                    request = urllib.request.Request(
                        url + route, json.dumps(payload).encode(), headers
                    )
                    with urllib.request.urlopen(request) as response:
                        return json.load(response)

                saved = post(
                    "/api/analyze", {"input": boot["example"], "label": "HTTP test"}
                )
                self.assertEqual(saved["run_id"], 1)
                scenarios = post(
                    "/api/scenarios",
                    {
                        "input": boot["example"],
                        "scenarios": [{"name": "same", "patches": []}],
                    },
                )
                self.assertEqual(scenarios["output"]["scenarios"][0]["changes"], [])
                batch = post("/api/batch", {"documents": [boot["example"], {}]})
                self.assertEqual(batch["output"]["successful"], 1)
                self.assertEqual(batch["output"]["failed"], 1)
                with urllib.request.urlopen(
                    urllib.request.Request(url + "/api/runs/1", headers=headers)
                ) as response:
                    record = json.load(response)
                self.assertEqual(record["label"], "HTTP test")
                self.assertEqual(record["output"], saved["output"])
                request = urllib.request.Request(
                    url + "/api/bootstrap",
                    headers={"Origin": "https://untrusted.example"},
                )
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(request)
                self.assertEqual(context.exception.code, 403)
            finally:
                process.terminate()
                process.communicate(timeout=5)
