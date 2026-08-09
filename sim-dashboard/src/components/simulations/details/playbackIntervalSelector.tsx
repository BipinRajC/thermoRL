import { Listbox, Transition } from "@headlessui/react";
import { Fragment } from "react";
import { Tooltip } from "react-tooltip";

const intervals = [15, 30, 60, 90, 120, 300, 600];

export function PlaybackIntervalSelector({
  value,
  onChange,
}: {
  value: number;
  onChange: (newValue: number) => void;
}) {
  return (
    <>
      <Listbox value={value} onChange={onChange}>
        <div className="relative">
          <Listbox.Button
            className={`w-[60px] rounded-md py-1 dark:text-neutral-200 dark:hover:bg-neutral-600`}
            data-tooltip-id="playback-interval-selector"
            data-tooltip-content="Playback Interval in Seconds"
            data-tooltip-delay-show={750}
          >
            {value}s
          </Listbox.Button>
          <Transition
            as={Fragment}
            leave="transition ease-in duration-300"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options
              className={
                "absolute bottom-full right-0 z-10 mb-1 flex flex-col gap-1 rounded-md bg-white py-2 text-center dark:bg-neutral-700"
              }
            >
              {[...intervals].reverse().map((interval) => (
                <Listbox.Option
                  key={interval}
                  value={interval}
                  className={({ selected }) =>
                    `cursor-pointer px-4 transition-colors duration-300 ease-in-out ${selected ? "text-blue-500" : "hover:bg-neutral-100 dark:text-neutral-200 dark:hover:bg-neutral-600"}`
                  }
                >
                  {interval}s
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>
      <Tooltip id="playback-interval-selector" />
    </>
  );
}
