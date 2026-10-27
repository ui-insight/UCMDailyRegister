import { useId, useRef, useState } from 'react';

interface Props {
  file: File | null;
  onChange: (file: File | null) => void;
}

export default function ImageUpload({ file, onChange }: Props) {
  const instructionsId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null;
    onChange(selected);
    if (selected) {
      const url = URL.createObjectURL(selected);
      setPreview(url);
    } else {
      setPreview(null);
    }
  };

  const handleRemove = () => {
    onChange(null);
    setPreview(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div>
      <p className="block text-sm font-medium text-gray-700 mb-1">
        Image (optional)
      </p>
      <p id={instructionsId} className="text-xs text-gray-500 mb-2">
        For Highlighted Events in My UI, images should be at least 600x600 pixels.
      </p>
      {preview ? (
        <div className="flex items-start gap-4">
          <img
            src={preview}
            alt="Preview"
            className="w-24 h-24 object-cover rounded-md border border-gray-200"
          />
          <div>
            <p className="text-sm text-gray-700">{file?.name}</p>
            <p className="text-xs text-gray-500">
              {file ? `${(file.size / 1024).toFixed(0)} KB` : ''}
            </p>
            <button
              type="button"
              onClick={handleRemove}
              className="mt-1 text-sm text-status-error-800 hover:text-red-700"
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        <button type="button" aria-describedby={instructionsId}
          onClick={() => inputRef.current?.click()}
          className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-ui-gold-400 transition-colors"
        >
          <span className="block text-sm text-gray-500">Choose an image</span>
          <span className="block text-xs text-gray-600 mt-1">JPG, PNG, GIF, WebP up to 10MB</span>
        </button>
      )}
      <input
        aria-label="Upload announcement image"
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleChange}
        className="hidden"
      />
    </div>
  );
}
