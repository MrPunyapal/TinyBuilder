"""Audit the exact Cargo.lock with OSV. No model or executable downloads."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import tomllib
import urllib.request

URL = "https://api.osv.dev/v1/querybatch"
MAX_RESPONSE = 8 * 1024 * 1024

def packages(lock):
    data = tomllib.loads(lock.decode("utf-8"))
    result = set()
    for p in data["package"]:
        source = p.get("source")
        if source is None:
            continue
        if source != "registry+https://github.com/rust-lang/crates.io-index":
            raise ValueError("Unreviewed dependency source")
        name, version = p["name"], p["version"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or not re.fullmatch(r"[0-9A-Za-z.+-]+", version):
            raise ValueError("Invalid lock dependency")
        result.add((name, version))
    if not result:
        raise ValueError("Empty dependency inventory")
    return sorted(result)

def query(rows):
    payload = {"queries": [{"package": {"name": n, "ecosystem": "crates.io"}, "version": v} for n,v in rows]}
    request = urllib.request.Request(URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "TinyBuilder-audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.geturl() != URL:
            raise ValueError("Unexpected audit endpoint")
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError("Oversized advisory response")
    return json.loads(raw)

def evaluate(rows, data):
    results = data.get("results")
    if not isinstance(results, list) or len(results) != len(rows):
        raise ValueError("Incomplete OSV result")
    findings = []
    for (name, version), row in zip(rows, results):
        if not isinstance(row, dict) or row.get("next_page_token"):
            raise ValueError("Incomplete OSV result")
        vulns = row.get("vulns", [])
        if not isinstance(vulns, list):
            raise ValueError("Invalid vulnerability list")
        for vuln in vulns:
            ident = vuln.get("id")
            if not isinstance(ident,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",ident):
                raise ValueError("Invalid advisory identifier")
            findings.append({"name":name,"version":version,"id":ident})
    return findings

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    raw=args.lock.read_bytes()
    report={"lock_sha256":hashlib.sha256(raw).hexdigest(),
        "checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source":URL,"status":"incomplete","findings":[]}
    try:
        rows=packages(raw)
        report["packages"]=[{"name":n,"version":v} for n,v in rows]
        findings=[]
        for i in range(0,len(rows),50):
            chunk=rows[i:i+50]
            findings.extend(evaluate(chunk,query(chunk)))
        report["findings"]=findings
        report["status"]="findings" if findings else "no known OSV matches"
    except Exception as error:
        report["error_type"]=type(error).__name__
    with args.output.open("x",encoding="utf-8") as file:
        json.dump(report,file,indent=2,sort_keys=True)
        file.write("\n")
    print(report["status"])
    return 0 if report["status"]=="no known OSV matches" else 1

if __name__=="__main__":
    raise SystemExit(main())
