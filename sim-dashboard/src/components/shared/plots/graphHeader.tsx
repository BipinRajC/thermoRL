export function GraphHeader(props: { children: React.ReactNode }) {
  return (
    <h4 className="text-center text-neutral-600 dark:text-neutral-400">
      {props.children}
    </h4>
  );
}
