import Button from './Button';
import Card from './Card';

export default function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  framed = true,
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  framed?: boolean;
}) {
  const content = (
    <div className="p-8 text-center">
      <div className="mx-auto mb-4 h-12 w-12 rounded-full border border-dashed border-ui-clearwater-300 bg-ui-clearwater-50" />
      <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-gray-500">{description}</p>
      {actionLabel && onAction && (
        <div className="mt-4">
          <Button variant="primary" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );

  if (!framed) return content;

  return <Card padded={false}>{content}</Card>;
}
