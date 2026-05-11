// components/chat/AssistantMessageContent.jsx

import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function AssistantMessageContent({ content }) {
  return (
    <div className="text-sm text-text leading-relaxed">
      <ReactMarkdown
        components={{
          // strip the <pre> wrapper so code handles its own container
          pre({ children }) {
            return <>{children}</>;
          },
          // inline code: no className; block code: className="language-xxx"
          code({ className, children }) {
            const language = className?.replace("language-", "") ?? "text";
            if (!className) {
              return (
                <code className="px-1 py-0.5 bg-surface-highest border border-border rounded-lg text-xs font-mono text-text">
                  {children}
                </code>
              );
            }
            // code block
            return (
              <div className="my-2 rounded-md border border-border bg-surface-high overflow-hidden">
                <div className="px-3 py-1 text-xs text-text-subtle font-mono">
                  {language}
                </div>
                <SyntaxHighlighter
                  language={language}
                  style={oneDark}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    padding: "0.75rem",
                    background: "transparent",
                    borderRadius: 0,
                    fontSize: "0.75rem",
                    lineHeight: "1.6",
                  }}
                  codeTagProps={{
                    style: { background: "transparent", border: "none" },
                  }}
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              </div>
            );
          },
          // paragraphs
          p({ children }) {
            return <p className="mb-2 last:mb-0 text-text">{children}</p>;
          },
          // bold
          strong({ children }) {
            return (
              <strong className="font-semibold text-text">{children}</strong>
            );
          },
          // lists
          ul({ children }) {
            return (
              <ul className="list-disc list-inside mb-2 space-y-1 text-text">
                {children}
              </ul>
            );
          },
          ol({ children }) {
            return (
              <ol className="list-decimal list-inside mb-2 space-y-1 text-text">
                {children}
              </ol>
            );
          },
          // headings
          h3({ children }) {
            return (
              <h3 className="font-semibold text-text mt-3 mb-1">{children}</h3>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
