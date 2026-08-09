import { BaseSyntheticEvent } from "react";
import { SharedDatePicker } from "../../datepicker";
import { Select } from "../../dropdown";
import { Input } from "../../input";

export function FilterInput(props: {
  fieldType: "datetime" | "select" | "text";
  choices: { label: string; value: string }[];
  onChange: (value: string | null) => void;
  value: string;
}) {
  const onChange = (e: BaseSyntheticEvent) => {
    props.onChange(e.target.value);
  };

  switch (props.fieldType) {
    case "text":
      return (
        <Input
          placeholder="Filter Value"
          value={props.value}
          onChange={onChange}
        />
      );
    case "select":
      return (
        <Select
          value={props.value}
          choices={props.choices}
          onChange={onChange}
          placeholder="Filter Value"
        />
      );
    case "datetime":
      return (
        <SharedDatePicker
          value={props.value || new Date().toISOString()}
          onChange={props.onChange}
        />
      );
    default:
      return null;
  }
}
