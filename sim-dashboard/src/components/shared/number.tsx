import { HTMLProps } from "react";

export interface NumberInputProps extends HTMLProps<HTMLDivElement> {
  label?: string;
  inputProps: HTMLProps<HTMLInputElement>;
  error?: { error: boolean; errorText: string };
  labelAlignment?: "vertical" | "horizontal";
}

export function NumberInput({labelAlignment, ...props}: NumberInputProps) {
  return (
    <div
      className={
        props.className +
        ` ${labelAlignment === "horizontal" ? "flex flex-row items-center gap-2" : "flex flex-col"} ${props.label ? "h-20" : "h-11"}`
      }
    >
      {props.label && (
        <label className="pl-3 dark:text-neutral-200">{props.label}</label>
      )}
      <input
        {...props.inputProps}
        type="number"
        className={
          props.inputProps.className +
          " h-10 flex-1 border-b-2 border-neutral-400 bg-transparent px-2 transition-all duration-300 ease-in-out hover:border-blue-500 focus:border-blue-500 focus:outline-none dark:text-neutral-200 " +
          `${props.error?.error && "border-red-600"}`
        }
      />
      {props.error?.error && (
        <span className="text-red-600">{props.error.errorText}</span>
      )}
    </div>
  );
}
