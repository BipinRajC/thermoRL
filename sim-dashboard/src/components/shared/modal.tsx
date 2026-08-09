export function Modal({
  open,
  children,
}: {
  open: boolean;
  children: JSX.Element | JSX.Element[];
}) {
  if (!open) return null;

  return (
    <div className="absolute left-0 top-0 z-50 flex h-full w-full items-center justify-center">
      <div className="absolute h-full w-full bg-neutral-800 opacity-50" />
      <div className="absolute flex h-2/3 w-2/3 flex-col rounded-md border-neutral-200 bg-white dark:bg-neutral-700  dark:text-neutral-200">
        {children}
      </div>
    </div>
  );
}
