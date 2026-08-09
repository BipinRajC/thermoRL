import { useState } from "react";
import DatePicker from "react-datepicker";
import { parseISO } from "date-fns";
import { CalendarIcon } from "@heroicons/react/24/outline";

export interface DatePickerProps {
  label?: string;
  onChange: (value: string | null) => void;
  value: string;
  boundedDate?: Date;
}

export function SharedDatePicker(props: DatePickerProps) {
  const [date, setDate] = useState(props.value ? parseISO(props.value) : null);

  return (
    <div className={`flex w-full flex-col ${props.label ? "h-20" : "h-11"}`}>
      {props.label && (
        <label htmlFor="start-date" className="mb-2 pl-3 dark:text-neutral-200">
          {props.label}
        </label>
      )}
      <DatePicker
        showIcon
        selected={date}
        onChange={(newDate, e) => {
          e?.preventDefault();
          newDate?.setMilliseconds(0);
          setDate(newDate);
          props.onChange(newDate?.toISOString() || null);
        }}
        toggleCalendarOnIconClick
        showTimeSelect
        className="w-full flex-1 border-b-2 border-neutral-400 bg-transparent !px-2 !py-2 !pr-9 transition-colors duration-300 hover:border-blue-500 focus:border-blue-500 focus:outline-none dark:text-neutral-200"
        minDate={props.boundedDate}
        dateFormat="MM/dd/yyyy, HH:mm z"
        icon={
          <CalendarIcon className="right-0 h-5 w-5 cursor-pointer transition-colors duration-500 hover:text-blue-500 dark:text-neutral-200" />
        }
      />
    </div>
  );
}
