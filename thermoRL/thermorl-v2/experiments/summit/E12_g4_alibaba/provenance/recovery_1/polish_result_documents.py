from pathlib import Path
ROOT=Path('/home/bipin/thermoRL');out=ROOT/'thermoRL/thermorl-v2/experiments/summit/E12_g4_alibaba'
replacements={'Task14':'Task 14','Tasks15–17':'Tasks 15–17','Task15–17':'Tasks 15–17','All15':'All 15','all15':'all 15','Full7200s':'Full 7200 s','warm-up,2160':'warm-up, 2160','and21600s':'and 21600 s','TPseed1':'TP seed 1','other14':'other 14','within1e-6kW':'within 1e-6 kW','independent2160-step/21600s':'independent 2160-step/21600 s','1.8189894035458565e-12kW':'1.8189894035458565e-12 kW','Reuse4 + restart3 + first-attempt8':'Reusing 4 complete runs, restarting 3 interrupted configurations and executing 8 previously unstarted configurations','selected15':'selected 15','packingseed2':'packing seed 2','node_balanceseed2':'node_balance seed 2','exceed25 MB':'exceed 25 MB','exited143':'exited 143','around45':'around 45','above70°C':'above 70°C','is0.6':'is 0.6','queues694/564/577':'queues of 694/564/577','waits≈290':'waits ≈290','in30.93s':'in 30.93 s','=189 passed':'= 189 passed','+28 integration':'+ 28 integration','complete19-attempt':'complete 19-attempt','strict3600':'strict 3600','must be≥0.5°C':'must be ≥0.5°C','means26':'means 26','use10s':'use 10 s','use10s':'use 10 s','use10s':'use 10 s','fractions use10s':'fractions use 10 s','in every seed at full precision.':'in every seed at full precision.'}
def polish(t):
    for a,b in replacements.items():t=t.replace(a,b)
    t=t.replace('derived separately below','derived separately in the E12 README and attribution record')
    t=t.replace('Service memory and process RSS have different scopes.','The follow-up service cgroup high-water was 6414262272 bytes (5.973748 GiB), spanning the guarded repeat, comparison and report. Both services exited successfully with zero restarts and remain available for inspection. Service memory and process RSS have different scopes.')
    t=t.replace('Recovery first-wave process walls:','Recovery first-wave process walls (node_balance seed2, packing seed2, TP seed1, in completion order):')
    t=t.replace('Original first-wave process walls:','Original first-wave process walls (packing, node_balance, power_balance seed1):')
    return t
p=out/'README.md';t=p.read_text()
sections=['Results','Plots','Observations (FACT)','Interpretation (INFERENCE)','Conclusion and decision','Task14 completion and operational recovery (2026-10-31)']
for name in sections:
    head='## '+name+'\n';start=t.index(head)+len(head);end=t.find('\n## ',start)
    if end<0:end=len(t)
    t=t[:start]+polish(t[start:end])+t[end:]
t=t.replace('## Task14 completion and operational recovery','## Task 14 completion and operational recovery')
t=t.replace('Any eventual result must remain scoped to the frozen rule, mapped Alibaba-derived input and Summit FMU. Task 15–17 and every policy simulation remain outside this assignment.','The result remains scoped to the frozen rule, mapped Alibaba-derived input and Summit FMU. Tasks 15–17 remain outside this assignment.')
p.write_text(t)
p=ROOT/'docs/checkpoints/C4-g4-alibaba.md';p.write_text(polish(p.read_text()))
# Preserve the exact helper used to construct result documentation.
with (out/'provenance/recovery_1/build_result_documents.py').open('xb') as f:f.write(Path('/tmp/e12_docs.py').read_bytes())
with (out/'provenance/recovery_1/polish_result_documents.py').open('xb') as f:f.write(Path('/tmp/e12_polish.py').read_bytes())
