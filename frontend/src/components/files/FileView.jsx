import { Prism as PrismHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

// Language map: file extension → react-syntax-highlighter language id
const LANG_MAP = {
  py: "python",
  js: "javascript",
  jsx: "jsx",
  mjs: "javascript",
  cjs: "javascript",
  ts: "typescript",
  tsx: "tsx",
  html: "html",
  css: "css",
  scss: "scss",
  sass: "sass",
  json: "json",
  md: "markdown",
  mdx: "markdown",
  yml: "yaml",
  yaml: "yaml",
  sh: "bash",
  bash: "bash",
  ini: "ini",
  toml: "toml",
  sql: "sql",
};

// File icon colours — matches FileTree
const ICON_COLORS = {
  py: "#60a5fa",
  js: "#fbbf24",
  jsx: "#fbbf24",
  mjs: "#fbbf24",
  cjs: "#fbbf24",
  ts: "#60a5fa",
  tsx: "#60a5fa",
  html: "#f97316",
  css: "#60a5fa",
  scss: "#e879f9",
  sass: "#e879f9",
  json: "#fbbf24",
  md: "#a1a1aa",
  mdx: "#a1a1aa",
};

import { VscFile, VscJson, VscMarkdown, VscSymbolColor } from "react-icons/vsc";
import { SiPython, SiJavascript, SiTypescript, SiHtml5 } from "react-icons/si";

const ICON_MAP = {
  py: SiPython,
  js: SiJavascript,
  jsx: SiJavascript,
  mjs: SiJavascript,
  cjs: SiJavascript,
  ts: SiTypescript,
  tsx: SiTypescript,
  html: SiHtml5,
  css: VscSymbolColor,
  scss: VscSymbolColor,
  sass: VscSymbolColor,
  json: VscJson,
  md: VscMarkdown,
  mdx: VscMarkdown,
};

function getExt(filename) {
  return filename?.split(".").pop()?.toLowerCase() ?? "";
}

function getFileIcon(filename) {
  const ext = getExt(filename);
  return {
    Icon: ICON_MAP[ext] ?? VscFile,
    color: ICON_COLORS[ext] ?? "#71717a",
  };
}

function getLang(filename) {
  return LANG_MAP[getExt(filename)] ?? "text";
}

// Override the vscDarkPlus background so it blends with our surface token
const HIGHLIGHTER_STYLE = {
  ...vscDarkPlus,
  'pre[class*="language-"]': {
    ...vscDarkPlus['pre[class*="language-"]'],
    background: "transparent",
    margin: 0,
    padding: 0,
    fontSize: "0.75rem",
    lineHeight: "1.6",
    fontFamily: "var(--font-mono)",
  },
  'code[class*="language-"]': {
    ...vscDarkPlus['code[class*="language-"]'],
    background: "transparent",
    fontSize: "0.75rem",
    lineHeight: "1.6",
    fontFamily: "var(--font-mono)",
  },
};

export default function FileView({
  filename = "untitled",
  content = "",
  className = "",
}) {
  const { Icon, color } = getFileIcon(filename);
  const lang = getLang(filename);
  const lines = content.split("\n");
  const lineCount = lines.length;
  const gutterWidth = String(lineCount).length;

  return (
    <div
      className={`flex flex-col h-full bg-surface overflow-hidden ${className}`}
    >
      {/* Title bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border shrink-0 bg-surface-raised">
        <Icon style={{ color }} className="shrink-0 text-sm" aria-hidden />
        <span className="text-xs font-mono text-text truncate">{filename}</span>
      </div>

      {/* Code area */}
      <div className="flex-1 overflow-auto">
        <div className="flex min-w-max min-h-full">
          {/* Line numbers */}
          <div
            className="select-none text-right pr-4 pl-4 py-4 text-xs font-mono
              text-text-subtle border-r border-border bg-surface-raised shrink-0 leading-[1.6]"
            style={{ minWidth: `${gutterWidth + 3}ch` }}
            aria-hidden
          >
            {lines.map((_, i) => (
              <div key={i}>{i + 1}</div>
            ))}
          </div>

          {/* Highlighted code */}
          <div className="flex-1 py-4 px-4 overflow-x-auto">
            <PrismHighlighter
              language={lang}
              style={HIGHLIGHTER_STYLE}
              useInlineStyles
              wrapLines={false}
              PreTag="div"
              CodeTag="div"
            >
              {content}
            </PrismHighlighter>
          </div>
        </div>
      </div>
    </div>
  );
}
