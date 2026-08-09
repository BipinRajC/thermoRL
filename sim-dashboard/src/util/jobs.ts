import { Job } from "../models/Job.model";
import { DateLike } from "./datetime";
import { isBefore, isAfter, isEqual } from "date-fns";

export const computeJobState = (job: Job, timestamp?: DateLike) => {
  if (timestamp) {
    if (isAfter(job.time_submission, timestamp)) {
      return "UNSUBMITTED"
    } else if (!job.time_start || isBefore(timestamp, job.time_start)) {
      return "PENDING";
    } else if (
      (isAfter(timestamp, job.time_start) || isEqual(timestamp, job.time_start)) &&
      (!job.time_end || isBefore(timestamp, job.time_end))
    ) {
      return "RUNNING";
    } else {
      return job.state_current;
    }
  } else {
    return job.state_current;
  }
};
