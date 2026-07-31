import { readdir, readFile } from "node:fs/promises";
import {
  basename,
  dirname,
  extname,
  join,
  relative,
  resolve,
  sep,
} from "node:path";
import { fileURLToPath } from "node:url";

const EXCLUDED_DIRECTORY_NAMES = new Set([
  ".git",
  ".venv",
  "__pycache__",
  ".pytest_cache",
  ".ruff_cache",
  ".pyinstaller-build",
  "build",
  "dist",
]);

const MENU_ITEMS = [
  ["../index.html", "ホーム"],
  ["../Requirement/index.html", "要求仕様書"],
  ["../DevelopmentPlan/index.html", "開発計画書"],
  ["../BasicDesign/index.html", "基本設計書"],
  ["../DetailDesign/index.html", "詳細設計書"],
  ["../TestSpecification/index.html", "テスト仕様書"],
  ["../TestResult/index.html", "テスト結果"],
  ["../DevelopmentResult/index.html", "開発実績"],
  ["../Program/index.html", "プログラム"],
  ["../Manual/index.html", "マニュアル"],
] as const;

const PAGE_TITLE = "ソフトウェア工学II「樹状整列」プログラム";

type DirectoryNode = {
  directories: Map<string, DirectoryNode>;
  files: string[];
};

type Arguments = {
  source: string;
  output: string;
};

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryDirectory = resolve(scriptDirectory, "..");

function parseArguments(arguments_: string[]): Arguments {
  let source = join(repositoryDirectory, "Forest_Program");
  let output = join(
    repositoryDirectory,
    "Forest_Document",
    "Program",
    "index.html",
  );
  for (let index = 0; index < arguments_.length; index += 1) {
    const argument = arguments_[index];
    if (argument === "--source" || argument === "--output") {
      const value = arguments_[index + 1];
      if (!value || value.startsWith("--")) {
        throw new Error(`${argument}にはパスを1つ指定してください。`);
      }
      if (argument === "--source") {
        source = resolve(value);
      } else {
        output = resolve(value);
      }
      index += 1;
      continue;
    }
    if (argument === "--help" || argument === "-h") {
      printHelp();
      process.exit(0);
    }
    throw new Error(`不明な引数です: ${argument}`);
  }

  return { source, output };
}

function printHelp(): void {
  console.log(`Pythonソースファイルを階層表示するHTMLを生成します。

Usage:
  bun scripts/show-source.ts [--source DIRECTORY] [--output FILE]

Options:
  --source DIRECTORY  収集対象（既定: Forest_Program）
  --output FILE       出力先（既定: Forest_Document/Program/index.html）
  -h, --help          このヘルプを表示`);
}

async function collectSourceFiles(sourceDirectory: string): Promise<string[]> {
  const sourceFiles: string[] = [];

  async function visit(directory: string): Promise<void> {
    const entries = await readdir(directory, { withFileTypes: true });
    entries.sort((left, right) => left.name.localeCompare(right.name));

    for (const entry of entries) {
      if (entry.isDirectory() && EXCLUDED_DIRECTORY_NAMES.has(entry.name)) {
        continue;
      }
      const path = join(directory, entry.name);
      if (entry.isDirectory()) {
        await visit(path);
      } else if (entry.isFile() && extname(entry.name) === ".py") {
        sourceFiles.push(path);
      }
    }
  }

  await visit(sourceDirectory);
  return sourceFiles;
}

function buildDirectoryTree(
  sourceDirectory: string,
  sourceFiles: string[],
): DirectoryNode {
  const tree: DirectoryNode = { directories: new Map(), files: [] };

  for (const sourceFile of sourceFiles) {
    const relativeParts = relative(sourceDirectory, sourceFile).split(sep);
    let node = tree;
    for (const directoryName of relativeParts.slice(0, -1)) {
      let child = node.directories.get(directoryName);
      if (!child) {
        child = { directories: new Map(), files: [] };
        node.directories.set(directoryName, child);
      }
      node = child;
    }
    node.files.push(sourceFile);
  }

  return tree;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function toPosixPath(path: string): string {
  return path.split(sep).join("/");
}

function buildAnchorId(sourceDirectory: string, sourceFile: string): string {
  return toPosixPath(relative(sourceDirectory, sourceFile)).replaceAll(
    /[^A-Za-z0-9_-]/g,
    "_",
  );
}

function sortedDirectories(node: DirectoryNode): [string, DirectoryNode][] {
  return [...node.directories.entries()].sort(([left], [right]) =>
    left.localeCompare(right),
  );
}

function renderMenu(): string {
  const items = MENU_ITEMS.map(
    ([href, label]) =>
      `        <li><a href="${href}"${label === "プログラム" ? ' class="current"' : ""}>${label}</a></li>`,
  ).join("\n");
  return `<div id="menu">
      <ul>
${items}
      </ul>
    </div>
    <hr />
    <h2>${PAGE_TITLE}</h2>`;
}

function renderTableOfContents(
  sourceDirectory: string,
  node: DirectoryNode,
): string {
  const files = [...node.files]
    .sort((left, right) => basename(left).localeCompare(basename(right)))
    .map(
      (sourceFile) =>
        `<li><a href="#${buildAnchorId(sourceDirectory, sourceFile)}">${escapeHtml(basename(sourceFile))}</a></li>`,
    );
  const directories = sortedDirectories(node).map(
    ([directoryName, child]) => `<li><span>${escapeHtml(directoryName)}</span>
<ul>
${renderTableOfContents(sourceDirectory, child)}
</ul>
</li>`,
  );
  return [...files, ...directories].join("\n");
}

async function renderDirectoryNode(
  sourceDirectory: string,
  node: DirectoryNode,
  depth = 0,
): Promise<string> {
  const headingLevel = Math.min(depth + 3, 6);
  const files: string[] = [];

  for (const sourceFile of [...node.files].sort((left, right) =>
    basename(left).localeCompare(basename(right)),
  )) {
    const anchorId = buildAnchorId(sourceDirectory, sourceFile);
    const displayPath = escapeHtml(
      toPosixPath(relative(sourceDirectory, sourceFile)),
    );
    const sourceCode = escapeHtml(await readFile(sourceFile, "utf8"));
    files.push(`<article class="source-file">
  <div class="belt">
    <h${headingLevel}><a id="${anchorId}" href="#${anchorId}">${displayPath}</a></h${headingLevel}>
  </div>
  <pre><code>${sourceCode}</code></pre>
</article>`);
  }

  const directories: string[] = [];
  for (const [directoryName, child] of sortedDirectories(node)) {
    directories.push(`<section class="source-directory">
  <div class="belt">
    <h${headingLevel}>${escapeHtml(directoryName)}</h${headingLevel}>
  </div>
  <div class="directory-children">
${await renderDirectoryNode(sourceDirectory, child, depth + 1)}
  </div>
</section>`);
  }

  return [...files, ...directories].join("\n");
}

async function renderHtml(
  sourceDirectory: string,
  sourceFiles: string[],
): Promise<string> {
  const tree = buildDirectoryTree(sourceDirectory, sourceFiles);
  const sourceName = escapeHtml(basename(sourceDirectory));
  const tableOfContents = renderTableOfContents(sourceDirectory, tree);
  const content = await renderDirectoryNode(sourceDirectory, tree);
  const today = new Date().toISOString().slice(0, 10);

  return `<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="description" content="${PAGE_TITLE}" />
    <link rel="stylesheet" href="../assets/css/docs.css" />
    <title>${PAGE_TITLE}</title>
    <style>
      .source-layout { display: flex; align-items: flex-start; gap: 20px; }
      .source-toc {
        position: sticky;
        top: 10px;
        flex: 0 0 280px;
        max-height: calc(100vh - 20px);
        overflow: auto;
        box-sizing: border-box;
        padding: 12px;
        border: 1px solid #cccccc;
        background: #f7f7f7;
      }
      .source-toc h3 { margin-top: 0; }
      .source-toc ul { margin: 0; padding-left: 18px; }
      .source-toc li { margin: 3px 0; }
      .source-content { min-width: 0; flex: 1 1 auto; }
      .source-directory { margin-bottom: 16px; }
      .directory-children { margin-left: 18px; }
      .source-file pre {
        overflow: auto;
        padding: 12px;
        border: 1px solid #dddddd;
        background: #fafafa;
        tab-size: 4;
      }
    </style>
  </head>
  <body>
    ${renderMenu()}
    <div class="source-layout">
      <nav class="source-toc" aria-label="ソースファイル目次">
        <h3>${sourceName}</h3>
        <ul>
${tableOfContents}
        </ul>
      </nav>
      <main class="source-content">
${content}
      </main>
    </div>
    <hr />
    <div class="right-small">Copyright SEForest Project, Updated: ${today}</div>
  </body>
</html>
`;
}

async function main(): Promise<void> {
  const arguments_ = parseArguments(process.argv.slice(2));
  const sourceFiles = await collectSourceFiles(arguments_.source);
  const htmlContent = await renderHtml(arguments_.source, sourceFiles);

  await Bun.write(arguments_.output, htmlContent);
  console.log(
    `生成しました: ${arguments_.output}（${sourceFiles.length}ファイル）`,
  );
}

await main();
