"""Science-Parse converter (fast batch mode).

Tuned for machines with around 32 GB of RAM.
"""

import os
import subprocess
from pathlib import Path

from ._backend_base import BasePDFConverter


class ScienceParseConverter(BasePDFConverter):
    def __init__(self, **kwargs):
        super().__init__()
        self.name = "Science-Parse Batch Engine"
        self.jar_path = kwargs.get("science_parse_jar", "libs/science-parse-cli.jar")

    @staticmethod
    def run_batch_mode(input_path: Path, output_path: Path, jar_path: str):
        """Run Science-Parse in native batch mode.

        A single JVM instance processes the whole directory, which is the
        fastest and most stable configuration.
        """
        java_cmd = "java"
        candidates = [
            "/usr/lib/jvm/java-8-openjdk-amd64/bin/java",
            "/usr/lib/jvm/java-1.8.0-openjdk-amd64/bin/java",
        ]
        for c in candidates:
            if os.path.exists(c) and os.access(c, os.X_OK):
                java_cmd = c
                break

        if not Path(jar_path).exists():
            print(f"ERROR: Science-Parse jar not found: {jar_path}")
            return

        print("\nRunning Science-Parse (fast batch mode)")
        print(f"Input:  {input_path}")
        print(f"Output: {output_path}")
        print(f"Java:   {java_cmd}")

        cmd = [
            java_cmd,
            "-Djava.security.egd=file:/dev/./urandom",
            "-Xverify:none",
            "-Xmx4g",
            "-XX:MaxDirectMemorySize=16g",
            "-Dorg.slf4j.simpleLogger.defaultLogLevel=error",
            "-Dorg.apache.commons.logging.Log=org.apache.commons.logging.impl.NoOpLog",
            "-jar",
            jar_path,
            "-o",
            str(output_path),
            str(input_path),
        ]

        print("Starting engine (first run loads models, ~5-10s)...")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            count = 0
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                if "DEBUG" in line or "WARN" in line:
                    continue

                if "Saved to" in line:
                    count += 1
                    fname = Path(line.split("Saved to")[-1].strip()).name
                    print(f"  [{count}] saved: {fname}")
                elif "Processing" in line:
                    print(f"  processing: {line.split('Processing')[-1].strip()}")
                elif "Error" in line:
                    print(f"  {line}")

            process.wait()

            if process.returncode == 0:
                print(f"\nDone. Results saved to: {output_path}")
            else:
                print(f"\nFinished with return code: {process.returncode}")

        except Exception as e:
            print(f"\nFatal error while running: {e}")

    def convert_single(self, pdf_path: Path):
        raise NotImplementedError("Science-Parse only supports fast batch mode; use run_batch_mode instead.")

    def get_info(self) -> dict:
        return {"name": self.name}
