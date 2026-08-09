import { ArrowDownIcon } from "@heroicons/react/24/outline";
import { ReactNode, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export function Header({ children }: { children: JSX.Element | string }) {
  return (
    <span className="border-b-2 border-neutral-200 pb-2 text-lg font-medium text-neutral-200">
      {children}
    </span>
  );
}

export function Section({
  header,
  defaultExpanded = true,
  flex = false,
  alwaysOpen = false,
  sectionProps,
  children,
}: {
  header: string;
  defaultExpanded?: boolean;
  flex?: boolean;
  alwaysOpen?: boolean;
  sectionProps?: Partial<HTMLDivElement>;
  children: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultExpanded);

  return (
    <div className="mt-4">
      <button
        className={`group flex w-full items-center justify-between border-b-2 border-neutral-400 pb-2 dark:border-neutral-200 dark:text-neutral-200 ${alwaysOpen && "cursor-default"}`}
        onClick={(e) => {
          e.preventDefault();
          if (!alwaysOpen) {
            setIsOpen((isOpen) => !isOpen);
          }
        }}
      >
        <span className="text-lg font-medium">{header}</span>
        {!alwaysOpen && (
          <ArrowDownIcon
            className={`h-5 w-5 transform transition-transform duration-500 ${!isOpen && "rotate-180"}`}
          />
        )}
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.section
            key="content"
            initial="collapsed"
            animate="open"
            exit="collapsed"
            variants={{
              open: { opacity: 1, height: "auto" },
              collapsed: { opacity: 0, height: 0 },
            }}
            transition={{ duration: 0.5, ease: [0.04, 0.62, 0.23, 0.98] }}
            className={`mt-2 w-full ${flex ? "flex flex-row gap-2" : "grid grid-cols-2 items-center gap-y-4 overflow-hidden"} ${sectionProps?.className}`}
            // Workaround for stack order bug: https://github.com/framer/motion/issues/2763
            style={{ willChange: 'auto' }}
          >
            {children}
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  );
}
