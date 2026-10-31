"""Construct fresh RAPS jobs from the immutable workload ledger."""

from raps.job import Job, job_dict

from thermorl2.raps_adapter.workload.synthetic import WORKLOAD_COLUMNS


def jobs_from_frame(frame):
    Job._id_counter = 0
    result = []
    for row in frame[WORKLOAD_COLUMNS].itertuples(index=False):
        assert row.time_limit >= row.expected_run_time
        assert float(row.expected_run_time).is_integer() and float(row.time_limit).is_integer()
        result.append(Job(job_dict(
            nodes_required=int(row.nodes_required), name=f"j{row.id}", account="demo", id=int(row.id),
            cpu_trace=float(row.cpu_util), gpu_trace=float(row.gpu_util), ntx_trace=0, nrx_trace=0,
            submit_time=float(row.submit_time), time_limit=int(row.time_limit), start_time=None, end_time=None,
            expected_run_time=int(row.expected_run_time),
        )))
    return result
