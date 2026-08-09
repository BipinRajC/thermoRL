import { HTMLProps } from "react";

export interface ButtonProps extends HTMLProps<HTMLButtonElement> {
  variant: "filled" | "outlined" | "text";
  type: "submit" | "reset" | "button";
  dense?: boolean;
}

export function Button({
  children,
  variant,
  type,
  dense,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`px-4 py-2 rounded-md transition-all duration-500 ${variant === "filled" && "bg-blue-500 text-white hover:opacity-75"} ${variant === "outlined" && `border-2 text-neutral-800 dark:text-neutral-200 dark:border-neutral-200 border-neutral-400 hover:opacity-50 ${rest.disabled && "opacity-75"}`} ${dense && "py-1"}`}
      {...rest}
    >
      {children}
    </button>
  );
}
