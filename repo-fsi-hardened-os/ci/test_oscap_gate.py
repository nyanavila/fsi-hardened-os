#!/usr/bin/env python3
"""Self-test for the compliance gate. Run: python3 ci/test_oscap_gate.py"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "oscap_gate.py")
R = "xccdf_org.ssgproject.content_rule_"
XML = ('<Benchmark xmlns="http://checklists.nist.gov/xccdf/1.2"><TestResult id="t">{rules}'
       '<score system="urn:xccdf:scoring:default" maximum="100">{score}</score></TestResult></Benchmark>')
RULE = '<rule-result idref="{r}"><result>{v}</result></rule-result>'


def run(rule_results, policy, score=80.0, raw_xml=None):
    with tempfile.TemporaryDirectory() as d:
        rx, pj = os.path.join(d, "r.xml"), os.path.join(d, "p.json")
        body = raw_xml if raw_xml is not None else XML.format(
            rules="".join(RULE.format(r=R + k, v=v) for k, v in rule_results.items()), score=score)
        open(rx, "w").write(body)
        json.dump(policy, open(pj, "w"))
        return subprocess.run([sys.executable, GATE, rx, pj], capture_output=True, text=True).returncode


BASE = {"blocking_rules": [R + "a", R + "b"], "waivers": {}, "min_score": 0, "on_notapplicable": "fail"}
CASES = [
    ("all blocking rules pass", {"a": "pass", "b": "pass", "c": "fail"}, BASE, {}, 0),
    ("non-blocking failures do not block", {"a": "pass", "b": "fixed", "z": "fail"}, BASE, {}, 0),
    ("one blocking rule fails", {"a": "pass", "b": "fail"}, BASE, {}, 1),
    ("blocking rule missing from results", {"a": "pass"}, BASE, {}, 1),
    ("blocking rule notselected", {"a": "pass", "b": "notselected"}, BASE, {}, 1),
    ("blocking rule error", {"a": "pass", "b": "error"}, BASE, {}, 1),
    ("notapplicable fails closed by default", {"a": "pass", "b": "notapplicable"}, BASE, {}, 1),
    ("notapplicable allowed when policy says so", {"a": "pass", "b": "notapplicable"},
     dict(BASE, on_notapplicable="allow"), {}, 0),
    ("waived failure does not block", {"a": "pass", "b": "pass", "w": "fail"},
     dict(BASE, waivers={R + "w": "documented reason"}), {}, 0),
    ("waiver without a reason blocks", {"a": "pass", "b": "pass", "w": "fail"},
     dict(BASE, waivers={R + "w": " "}), {}, 1),
    ("rule both blocking and waived blocks", {"a": "pass", "b": "fail"},
     dict(BASE, waivers={R + "b": "nope"}), {}, 1),
    ("score below floor blocks", {"a": "pass", "b": "pass"}, dict(BASE, min_score=90), {"score": 60.0}, 1),
    ("score above floor passes", {"a": "pass", "b": "pass"}, dict(BASE, min_score=50), {"score": 60.0}, 0),
    ("empty blocking list is refused", {"a": "pass"}, dict(BASE, blocking_rules=[]), {}, 3),
    ("garbage results file fails closed", {}, BASE, {"raw_xml": "not xml at all"}, 3),
    ("results with no rules fails closed", {}, BASE, {}, 3),
]

failed = 0
for name, rules, policy, kw, want in CASES:
    got = run(rules, policy, **kw)
    ok = got == want
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {name} (exit {got}, expected {want})")
print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
sys.exit(1 if failed else 0)
