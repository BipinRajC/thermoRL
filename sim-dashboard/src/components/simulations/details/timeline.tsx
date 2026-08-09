import { addSeconds, differenceInSeconds } from "date-fns";
import ReactSlider from "react-slider";
import { Tooltip } from "react-tooltip";
import { PlaybackRateSelector } from "./playbackRateSelector";
import { PlaybackIntervalSelector } from "./playbackIntervalSelector";
import { DateLike, formatDate } from "../../../util/datetime";

export interface TimelineProps {
  value: DateLike;
  start: DateLike;
  /** Will show a second "track" up to this point, e.g. so you can see simulation progress */
  available: DateLike;
  end: DateLike;
  onChange: (value: Date) => void;
  interval: number;
  rate: number;
  onIntervalChange: (newValue: number) => void;
  onRateChange: (newValue: number) => void;
}

export function Timeline(props: TimelineProps) {
  const prevStep = (d: number) => {
    if (d % props.interval == 0) {
      return Math.max(0, d - props.interval)
    } else {
      return d - (d % props.interval)
    }
  }

  const value = differenceInSeconds(props.value, props.start)
  const available = prevStep(differenceInSeconds(props.available, props.start))
  const max = prevStep(differenceInSeconds(props.end, props.start))

  return (
    <div className="flex w-full items-center gap-4">
      <ReactSlider
        min={0}
        max={max}
        step={props.interval}
        value={value}
        onChange={(value) => {
          props.onChange(addSeconds(props.start, Math.min(value, available)))
        }}
        orientation="horizontal"
        className="h-4 w-full"
        trackClassName="cursor-pointer h-2 rounded-full top-1 track"
        renderTrack={({key, className, ...trackProps}, state) => {
          if (state.index == 0) {
            return (<div key={key} className={className + " bg-blue-500"} {...trackProps}/>)
          } else {
            // index=1 is the part of the slider after the thumb.
            // We're adding a progress bar on top of it to show the simulation progress
            // react-slider supports multiple "tracks" which sort does what we want, but it adds
            // an extra thumb makes the second track interactable, so its easier to just do set it
            // up here.
            const percent = 100 * (available - value) / (max - value)
            return (
              <div
                key={key}
                className={className + " bg-neutral-200 dark:bg-neutral-700"}
                {...trackProps}
              >
                <div
                  className="h-full rounded-full bg-neutral-300 dark:bg-neutral-600"
                  style={{width: `${percent}%`}}
                />
              </div>
            )
          }
        }}
        thumbClassName="bg-blue-500 h-4 w-4 rounded-full cursor-pointer thumb"
        renderThumb={({key, ...thumbProps}, state) => (
          <div
            key={key} {...thumbProps}
            data-tooltip-id="timeline-thumb"
            data-tooltip-content={`${formatDate(addSeconds(props.start, state.value))} / ${formatDate(props.end)}`}
          />
        )}
      />
      <PlaybackRateSelector value={props.rate} onChange={props.onRateChange} />
      <PlaybackIntervalSelector
        value={props.interval}
        onChange={props.onIntervalChange}
      />
      <Tooltip id="timeline-thumb" />
    </div>
  );
}
