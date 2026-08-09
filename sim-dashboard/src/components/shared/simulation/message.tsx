import { ReactNode } from "react";

export const Message = ({
  children,
}: {
  children: ReactNode;
}) => {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-lg text-neutral-800 dark:text-neutral-300">
        {children}
      </p>
    </div>
  );
};

