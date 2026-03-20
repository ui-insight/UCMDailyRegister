import { useMemo } from 'react';

interface RichBodyProps {
  text: string;
  className?: string;
}

/**
 * Renders body text with embedded HTML anchor tags as real links.
 * Only <a href="...">...</a> tags are rendered; all other HTML is escaped.
 */
export default function RichBody({ text, className = '' }: RichBodyProps) {
  const parts = useMemo(() => {
    const result: { type: 'text' | 'link'; text: string; href?: string }[] = [];
    const linkPattern = /<a\s+href=["']([^"']+)["'][^>]*>([^<]+)<\/a>/gi;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = linkPattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        result.push({ type: 'text', text: text.slice(lastIndex, match.index) });
      }
      result.push({ type: 'link', text: match[2], href: match[1] });
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      result.push({ type: 'text', text: text.slice(lastIndex) });
    }

    return result;
  }, [text]);

  return (
    <p className={`whitespace-pre-wrap ${className}`}>
      {parts.map((part, i) =>
        part.type === 'link' ? (
          <a
            key={i}
            href={part.href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            {part.text}
          </a>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </p>
  );
}
