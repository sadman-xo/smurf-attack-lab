# Smurf & Fraggle Attack Lab — Cloud Shell Tutorial

<walkthrough-tutorial-duration duration="10"></walkthrough-tutorial-duration>

## Welcome

This tutorial walks you through the **Smurf & Fraggle directed-broadcast amplification attack lab** entirely inside Google Cloud Shell. No VMs, no setup — just click through.

Click **Start** to begin.

## Install prerequisites

Cloud Shell ships most tools we need. Install the two optional ones for full packet captures:

```bash
sudo apt-get update -qq && sudo apt-get install -y -qq tcpdump iputils-ping
```

Now check that this kernel can run the lab:

```bash
cd lab && sudo bash preflight.sh
```

If all required checks pass, continue. If bridge or bc_forwarding fails, this kernel can't run the lab (rare on Cloud Shell).

Click **Next** to build the lab.

## Build the lab

This creates 6 network namespaces (attacker, victim, router, amp1-3) with the deliberately vulnerable configuration:

```bash
sudo bash setup_lab.sh
```

You should see the self-test confirm amplification is live for both Smurf and Fraggle.

Click **Next** to run the attacks.

## Run the full attack & defense matrix

One command reproduces every attack variant and every defense layer:

```bash
sudo bash run_all.sh
```

This runs:
- **Vulnerable baseline** — Smurf (ICMP) and Fraggle (UDP), both Python and C senders
- **Router defense** — bc_forwarding=0 (should collapse both to 0)
- **Amplifier ICMP defense** — stops Smurf only, Fraggle unchanged
- **Service defense** — stops Fraggle only, Smurf unchanged
- **Spoofguard defense** — edge source guard, collapses both to 0
- **Revert & recheck** — confirms vulnerability restores

Watch the amplification factors in the output.

Click **Next** to run the scaling experiment.

## Amplifier-count scaling sweep

See how the amplification factor scales linearly with the number of amplifiers (1 through 8):

```bash
sudo AMP_COUNT=8 bash setup_lab.sh > /dev/null && sudo bash scale_test.sh
```

You should see factor(k) = k exactly.

Click **Next** to view results.

## View the results

Machine-readable results:

```bash
column -t -s $'\t' results/summary.tsv
```

Scaling data:

```bash
column -t -s $'\t' results/scaling.tsv
```

Verify a pcap independently:

```bash
tcpdump -r results/vulnerable-icmp-py-*.pcap 'icmp[icmptype]==icmp-echoreply' | wc -l
```

Click **Next** to clean up.

## Clean up

Remove all namespaces and processes:

```bash
sudo bash teardown_lab.sh
```

Nothing persists — all vulnerable settings lived only inside the namespaces.

## Done

You've reproduced the full Smurf & Fraggle attack study. Key takeaways:

- Both attacks achieve **amplification factor = number of amplifiers**
- The **router fix** (bc_forwarding=0) and **edge source guard** each stop both attacks
- Per-host fixes are protocol-specific — proving the **misconfiguration, not the protocol**, is the vulnerability

Full report: `reports/Final_Report_Group05_A2.pdf`

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>
