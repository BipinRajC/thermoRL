import { HTMLProps } from "react";

export interface TextAreaProps extends HTMLProps<HTMLTextAreaElement> {
  label?: string;
  labelAlignment?: "vertical" | "horizontal";
  error?: string;
}

export function TextArea({labelAlignment, ...props}: TextAreaProps) {
  return (
    <div
      className={`${labelAlignment === "horizontal" ? "flex flex-row items-center" : "flex flex-col"} gap-2 ${props.className}`}
    >
      {props.label && (
        <label className="pl-3 dark:text-neutral-200">
          {props.label}
        </label>
      )}
      <textarea
        {...props}
        className="flex-1 border-2 border-neutral-400 bg-transparent px-2 py-2 transition-colors duration-300 hover:border-blue-500 focus:border-blue-500 focus:outline-none dark:text-neutral-200"
        onChange={props.onChange}
        value={props.value}
      />
      {props.error && (
        <span className="text-red-600">{props.error}</span>
      )}
    </div>
  );
}
