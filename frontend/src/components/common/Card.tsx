import type { HTMLAttributes, ReactNode } from 'react';
import { cx } from './utils';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  padded?: boolean;
}

export default function Card({
  children,
  className,
  padded = true,
  ...props
}: CardProps) {
  return (
    <div
      className={cx('rounded-lg bg-white shadow', padded && 'p-4', className)}
      {...props}
    >
      {children}
    </div>
  );
}
