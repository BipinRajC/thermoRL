import pandas as pd
import pytest

from thermorl2.experiments import workload_regime


def test_exact_offered_event_integration_hourly_and_overload():
    frame=pd.DataFrame(dict(submit_time=[0.,5.],expected_run_time=[10,10],nodes_required=[10,5]))
    result=workload_regime.offered_profile(frame,10,20,window_start_s=0,hour_s=10)
    assert result['hourly_arrivals']==[2,0]
    assert result['hourly_mean_offered_utilisation']==pytest.approx([1.25,.25])
    assert result['window_mean_offered_utilisation']==.75
    assert result['window_min_offered_utilisation']==0
    assert result['window_max_offered_utilisation']==1.5
    assert result['window_fraction_above_1']==.25


def test_creation_concentration_counts_largest_gaps():
    result=workload_regime.creation_concentration([0.,0.,5.,10.])
    assert result['span_s']==10
    assert result['quantiles_s']['0.5']==2.5
    assert result['largest_gap_span_shares']['1']==.5
    assert result['largest_gap_span_shares']['20']==1.
