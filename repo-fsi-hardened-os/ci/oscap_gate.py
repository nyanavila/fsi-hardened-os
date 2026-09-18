#!/usr/bin/env python3
"""Compliance gate for an OpenSCAP XCCDF results file.

Usage: oscap_gate.py <results.xml> <gate-policy.json>
Exit 0 = gate passed, 1 = gate failed, 3 = results unusable (fail closed).

Why not just use oscap's exit code? A full PCI-DSS profile has ~250 rules and
many cannot pass inside a container build (partitions, boot loader, audit
daemon state). "Fail on any finding" would block every image forever, which
is why the old pipeline swallowed the exit code. This gate makes the policy
explicit instead: a named list of rules that must pass, an optional score
floor, and written waivers. Standard library only.
"""
import json
import sys
import xml.etree.ElementTree as ET

NS = "{http://checklists.nist.gov/xccdf/1.2}"
SHORT = lambda rid: rid.split("content_rule_")[-1]


def load_results(path):
    root = ET.parse(path).getroot()
    tr = root if root.tag == NS + "TestResult" else next(root.iter(NS + "TestResult"), None)
    if tr is None:
        raise ValueError("no TestResult element found")
    results = {}
    for rr in tr.findall(NS + "rule-result"):
        res = rr.find(NS + "result")
        results[rr.get("idref")] = (res.text or "").strip() if res is not None else "unknown"
    score_el = tr.find(NS + "score")
    score = float(score_el.text) if score_el is not None and score_el.text else None
    return results, score


def evaluate(results, score, policy):
    """Return (problems, notes). Any problem fails the gate."""
    problems, notes = [], []
    na_mode = policy.get("on_notapplicable", "fail")
    waivers = policy.get("waivers", {})

    for rid in policy.get("blocking_rules", []):
        res = results.get(rid)
        if rid in waivers:
            problems.append(f"{SHORT(rid)}: listed as both blocking and waived; fix the policy")
        elif res == "pass" or res == "fixed":
            notes.append(f"PASS     {SHORT(rid)}")
        elif res == "notapplicable" and na_mode != "fail":
            notes.append(f"N/A      {SHORT(rid)} (allowed by on_notapplicable)")
        elif res is None or res == "notselected":
            problems.append(f"{SHORT(rid)}: not evaluated by this profile, so it proves nothing")
        else:
            problems.append(f"{SHORT(rid)}: result was '{res}'")

    for rid, reason in waivers.items():
        res = results.get(rid, "not evaluated")
        if not str(reason).strip():
            problems.append(f"{SHORT(rid)}: waiver has no written reason")
        notes.append(f"WAIVED   {SHORT(rid)} (result: {res}) - {reason}")

    floor = float(policy.get("min_score", 0) or 0)
    if floor > 0:
        if score is None:
            problems.append("min_score is set but the results contain no score")
        elif score < floor:
            problems.append(f"score {score:.1f} is below the required {floor:.1f}")
    return problems, notes


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 3
    try:
        results, score = load_results(argv[1])
        with open(argv[2]) as fh:
            policy = json.load(fh)
    except Exception as exc:  # unreadable evidence must never pass
        print(f"GATE ERROR: cannot read inputs ({exc}). Failing closed.")
        return 3
    if not results:
        print("GATE ERROR: results file contains no rule results. Failing closed.")
        return 3
    if not policy.get("blocking_rules"):
        print("GATE ERROR: policy has no blocking_rules; a gate that checks nothing is not a gate.")
        return 3

    problems, notes = evaluate(results, score, policy)
    counts = {}
    for r in results.values():
        if r != "notselected":
            counts[r] = counts.get(r, 0) + 1
    print("OpenSCAP compliance gate")
    print(f"  rules in profile: {sum(counts.values())}  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"  score: {score:.1f}" if score is not None else "  score: n/a")
    for n in notes:
        print("  " + n)
    if problems:
        print("\nGATE FAILED - image will not be published:")
        for p in problems:
            print("  BLOCKED  " + p)
            print(f"::error::Compliance gate: {p}")
        return 1
    print("\nGATE PASSED - all blocking controls satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
