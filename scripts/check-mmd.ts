import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { run } from "@mermaid-js/mermaid-cli";

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
    await run(inputFile, outputFile, {
      quiet: true,
      puppeteerConfig: process.env.CI
        ? { args: ["--no-sandbox", "--disable-setuid-sandbox"] }
        : {},
    });

    console.log(`[check:mmd] passed ${inputFile}`);
  }
} finally {
  await rm(outputDirectory, { recursive: true, force: true });
}
