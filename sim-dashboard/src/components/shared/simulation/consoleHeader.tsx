export function ConsoleHeader({ children }: { children: React.ReactNode }) {
  return (
    <h1 className="w-full text-center dark:text-neutral-200">{children}</h1>
  );
}
