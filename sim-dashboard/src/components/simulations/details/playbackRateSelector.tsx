import { Listbox, Transition } from "@headlessui/react";
import { Fragment } from "react";
import { Tooltip } from "react-tooltip";

const rates = [1, 2, 5, 10, 20, 50];

export function PlaybackRateSelector(props: {
  value: number;
  onChange: (newValue: number) => void;
}) {
  return (
    <>
      <Listbox value={props.value} onChange={props.onChange}>
        <div className="relative">
          <Listbox.Button
            className={`w-[60px] rounded-md py-1 dark:text-neutral-200 dark:hover:bg-neutral-600`}
            data-tooltip-id="playback-rate-selector"
            data-tooltip-content="Playback Rate"
            data-tooltip-delay-show={750}
          >
            {props.value}x
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
              {[...rates].reverse().map((rate) => (
                <Listbox.Option
                  key={rate}
                  value={rate}
                  className={({ selected }) =>
                    `cursor-pointer px-4 transition-colors duration-300 ease-in-out ${selected ? "text-blue-500" : "hover:bg-neutral-100 dark:text-neutral-200 dark:hover:bg-neutral-600"}`
                  }
                >
                  {rate}x
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>
      <Tooltip id="playback-rate-selector" />
    </>
  );
}
