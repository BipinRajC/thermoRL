import { HTMLProps } from "react";

export interface CheckboxProps extends HTMLProps<HTMLInputElement> {
  label?: string;
  WrapperProps?: Partial<HTMLDivElement>;
}

export function Checkbox({
  label,
  className,
  WrapperProps,
  ...rest
}: CheckboxProps) {
  return (
    <div
      className={`flex flex-col items-center ${label ? "h-20" : "h-11"} ${WrapperProps?.className}`}
    >
      {!!label && (
        <label htmlFor={label} className="mb-2 dark:text-neutral-200">
          {label}
        </label>
      )}
      <input
        type="checkbox"
        id={label}
        className={`flex-1 py-2 ${className}`}
        {...rest}
      />
    </div>
  );
}
