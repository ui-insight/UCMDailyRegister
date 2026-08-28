export type CopyResult = 'rich' | 'plain';

/**
 * Copy rich text (HTML plus a plain-text alternate) to the clipboard.
 *
 * Prefers the async ClipboardItem API so pastes into Outlook/Word keep
 * formatting and hyperlinks; browsers without text/html clipboard write
 * support fall back to plain text. The return value tells the caller which
 * flavor landed so the UI can say so.
 */
export async function copyHtmlToClipboard(
  html: string,
  text: string,
): Promise<CopyResult> {
  const clipboard = navigator.clipboard;
  if (!clipboard) {
    throw new Error('Clipboard access is not available in this browser.');
  }
  if (typeof ClipboardItem !== 'undefined' && clipboard.write) {
    try {
      await clipboard.write([
        new ClipboardItem({
          'text/html': new Blob([html], { type: 'text/html' }),
          'text/plain': new Blob([text], { type: 'text/plain' }),
        }),
      ]);
      return 'rich';
    } catch {
      // Fall through to the plain-text path.
    }
  }
  await clipboard.writeText(text);
  return 'plain';
}
