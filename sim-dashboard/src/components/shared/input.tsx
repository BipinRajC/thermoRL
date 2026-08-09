import { HTMLProps } from "react";

export interface InputProps extends HTMLProps<HTMLInputElement> {
  label?: string;
  labelAlignment?: "vertical" | "horizontal";
}

export function Input({labelAlignment, ...props}: InputProps) {
  return (
    <div
      className={`${labelAlignment === "horizontal" ? "flex flex-row items-center" : "flex flex-col"} gap-2 ${props.label ? "h-20" : "h-11"}`}
    >
      {props.label && (
        <label htmlFor="text-input" className="pl-3 dark:text-neutral-200">
          {props.label}
        </label>
      )}
      <input
        {...props}
        id="text-input"
        type="text"
        className="flex-1 border-b-2 border-neutral-400 bg-transparent px-2 py-2 transition-colors duration-300 hover:border-blue-500 focus:border-blue-500 focus:outline-none dark:text-neutral-200"
        onChange={props.onChange}
        value={props.value}
      />
    </div>
  );
}
