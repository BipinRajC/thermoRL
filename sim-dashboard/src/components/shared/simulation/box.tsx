import { ReactNode } from "react";

const Box = ({
  children,
}: {
  children: JSX.Element | JSX.Element[] | null;
}) => {
  return <div className="flex flex-col gap-2">{children}</div>;
};

const Header = ({ children }: { children: string }) => {
  return (
    <p className="text-md text-neutral-700 dark:text-neutral-400">
      {children}:
    </p>
  );
};

Box.Header = Header;

const Value = ({ children }: { children: ReactNode }) => {
  return (
    <p className="text-lg text-neutral-800 dark:text-neutral-300">{children}</p>
  );
};

Box.Value = Value;

export default Box;
