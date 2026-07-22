import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";

const mermaidFiles = [
  ...new Bun.Glob("**/*.mmd").scanSync({
    cwd: process.cwd(),
    onlyFiles: true,
  }),
].sort();

if (mermaidFiles.length === 0) {
  console.log("[check:mmd] Mermaidファイルはありません。");
  process.exit(0);
}

const outputDirectory = await mkdtemp(join(tmpdir(), "seforest-mmd-"));

try {
  for (const [index, inputFile] of mermaidFiles.entries()) {
    const outputFile = join(
      outputDirectory,
      `${index}-${basename(inputFile, ".mmd")}.svg`,
    );
    const renderProcess = Bun.spawn(
      [
        join(process.cwd(), "node_modules", ".bin", "mmdc"),
        "--input",
        inputFile,
        "--output",
        outputFile,
        "--quiet",
      ],
      {
        stdout: "inherit",
        stderr: "inherit",
      },
    );
    const exitCode = await renderProcess.exited;

    if (exitCode !== 0) {
      throw new Error(`${inputFile} のレンダリングに失敗しました。`);
    }

    console.log(`[check:mmd] passed ${inputFile}`);
  }
} finally {
  await rm(outputDirectory, { recursive: true, force: true });
}
