interface LinkEntry {
  url: string;
  anchor_text: string;
}

interface Props {
  links: LinkEntry[];
  onChange: (links: LinkEntry[]) => void;
}

export default function LinkEditor({ links, onChange }: Props) {
  const addLink = () => {
    onChange([...links, { url: '', anchor_text: '' }]);
  };

  const removeLink = (index: number) => {
    onChange(links.filter((_, i) => i !== index));
  };

  const updateLink = (index: number, field: keyof LinkEntry, value: string) => {
    const updated = links.map((link, i) =>
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
        Add URLs you'd like embedded in your announcement with the text they should be linked to.
      </p>
      {links.map((link, index) => (
        <div key={index} className="flex gap-2 mb-2">
          <input
            type="url"
            placeholder="https://..."
            value={link.url}
            onChange={(e) => updateLink(index, 'url', e.target.value)}
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
          />
          <input
            type="text"
            placeholder="Link text (e.g., 'Learn more')"
            value={link.anchor_text}
            onChange={(e) => updateLink(index, 'anchor_text', e.target.value)}
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
          />
          <button
            type="button"
            onClick={() => removeLink(index)}
            className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md"
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={addLink}
        className="text-sm text-amber-600 hover:text-amber-700 font-medium"
      >
        + Add Link
      </button>
    </div>
  );
}
