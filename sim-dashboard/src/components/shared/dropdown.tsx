import { ChangeEvent, HTMLProps } from "react";

export interface SelectProps extends HTMLProps<HTMLSelectElement> {
  choices: { label: string; value: string }[];
  label?: string;
  value: string;
  onChange: (e: ChangeEvent<HTMLSelectElement>) => void;
}

export function Select({onChange, value, choices, ...props}: SelectProps) {
  return (
    <div className={`flex flex-col ${props.label ? "h-20" : "h-11"}`}>
      {props.label && (
        <label className="mb-2 pl-3 dark:text-neutral-200">{props.label}</label>
      )}
      <select
        {...props}
        onChange={onChange}
        value={value}
        className={
          props.className +
          " flex-1 cursor-pointer border-b-2 border-neutral-400 bg-transparent px-2 py-2 transition-colors duration-300 ease-in-out hover:border-blue-500 focus:border-blue-500 focus:outline-none dark:text-neutral-200"
        }
      >
        <option disabled value="">
          {props.placeholder}
        </option>
        {choices.map((choice) => (
          <option
            key={choice.value}
            value={choice.value}
            className="text-black placeholder:text-neutral-500"
          >
            {choice.label}
          </option>
        ))}
      </select>
    </div>
  );
}
