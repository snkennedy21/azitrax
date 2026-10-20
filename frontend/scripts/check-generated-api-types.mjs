import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";

const frontendRoot = resolve(dirname(new URL(import.meta.url).pathname), "..");
const generatedPath = join(frontendRoot, "src/services/api/types.generated.ts");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "azitrax-api-types-"));
const temporaryPath = join(temporaryDirectory, "types.generated.ts");

try {
  execFileSync(
    "npx",
    [
      "--no-install",
      "openapi-typescript",
      "http://127.0.0.1:8000/openapi.json",
      "-o",
      temporaryPath,
      "--path-params-as-types",
    ],
    { cwd: frontendRoot, stdio: "inherit" },
  );

  const expected = readFileSync(generatedPath, "utf8");
  const actual = readFileSync(temporaryPath, "utf8");
  if (expected === actual) {
    process.stdout.write("Generated API types are current.\n");
  } else {
    process.stderr.write("Generated API types are out of date:\n");
    const diff = spawnSync("diff", ["-u", generatedPath, temporaryPath], {
      encoding: "utf8",
    });
    process.stderr.write(diff.stdout || "");
    process.exitCode = 1;
  }
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
