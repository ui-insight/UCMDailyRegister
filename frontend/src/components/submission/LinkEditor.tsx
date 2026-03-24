interface LinkEntry {
  Url: string;
  Anchor_Text: string;
}

interface Props {
  links: LinkEntry[];
  onChange: (links: LinkEntry[]) => void;
}

const MAX_LINKS = 3;

function ensureSlots(links: LinkEntry[]): LinkEntry[] {
  const slots = [...links];
  while (slots.length < MAX_LINKS) {
    slots.push({ Url: '', Anchor_Text: '' });
  }
  return slots.slice(0, MAX_LINKS);
}

export default function LinkEditor({ links, onChange }: Props) {
  const slots = ensureSlots(links);

  const updateLink = (index: number, field: keyof LinkEntry, value: string) => {
    const updated = slots.map((link, i) =>
      i === index ? { ...link, [field]: value } : link,
    );
    onChange(updated);
  };

  /** Detect whether a slot is storing a mailto: link. */
  const isEmailLink = (url: string) => url.startsWith('mailto:');

  /** Toggle between web URL and email mode for a slot. */
  const toggleLinkType = (index: number) => {
    const current = slots[index];
    if (isEmailLink(current.Url)) {
      // Switch to web — strip mailto: prefix
      updateLink(index, 'Url', '');
    } else {
      // Switch to email — clear URL and prepend mailto:
      updateLink(index, 'Url', 'mailto:');
    }
  };

  const handleEmailChange = (index: number, email: string) => {
    // Store with mailto: prefix
    updateLink(index, 'Url', `mailto:${email}`);
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Links to Embed
      </label>
      <p className="text-xs text-gray-500 mb-3">
        Add up to {MAX_LINKS} web URLs or email addresses to embed in your announcement.
      </p>
      <div className="space-y-3">
        {slots.map((link, index) => {
          const emailMode = isEmailLink(link.Url);
          return (
            <div key={index} className="rounded-md border border-gray-200 bg-gray-50 p-3">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-gray-500">Link {index + 1}</p>
                <button
                  type="button"
                  onClick={() => toggleLinkType(index)}
                  className="text-xs text-ui-gold-700 hover:text-ui-gold-800 font-medium"
                >
                  {emailMode ? 'Switch to web link' : 'Switch to email link'}
                </button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    {emailMode ? 'Email address' : 'URL'}
                  </label>
                  {emailMode ? (
                    <input
                      type="email"
                      placeholder="name@uidaho.edu"
                      value={link.Url.replace(/^mailto:/, '')}
                      onChange={(e) => handleEmailChange(index, e.target.value)}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                    />
                  ) : (
                    <input
                      type="url"
                      placeholder="https://..."
                      value={link.Url}
                      onChange={(e) => updateLink(index, 'Url', e.target.value)}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                    />
                  )}
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    {emailMode
                      ? "Link text (person's name or email address)"
                      : 'Words to link the URL to (e.g., Learn more.)'}
                  </label>
                  <input
                    type="text"
                    placeholder={emailMode ? "e.g., Jane Smith" : "e.g., Learn more"}
                    value={link.Anchor_Text}
                    onChange={(e) => updateLink(index, 'Anchor_Text', e.target.value)}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                  />
                </div>
              </div>
              {emailMode && (
                <p className="text-[11px] text-gray-400 mt-1.5">
                  For individual email addresses, use the person's name as the link text. For general addresses, the email address itself is fine.
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
