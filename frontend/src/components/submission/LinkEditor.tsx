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

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Links to Embed
      </label>
      <p className="text-xs text-gray-500 mb-3">
        Add up to {MAX_LINKS} URLs you'd like embedded in your announcement.
      </p>
      <div className="space-y-3">
        {slots.map((link, index) => (
          <div key={index} className="rounded-md border border-gray-200 bg-gray-50 p-3">
            <p className="text-xs font-medium text-gray-500 mb-2">Link {index + 1}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-gray-500 mb-1">URL</label>
                <input
                  type="url"
                  placeholder="https://..."
                  value={link.Url}
                  onChange={(e) => updateLink(index, 'Url', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Words to link the URL to (e.g., Learn more.)
                </label>
                <input
                  type="text"
                  placeholder="e.g., Learn more"
                  value={link.Anchor_Text}
                  onChange={(e) => updateLink(index, 'Anchor_Text', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-ui-gold-500 focus:ring-1 focus:ring-ui-gold-500"
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
