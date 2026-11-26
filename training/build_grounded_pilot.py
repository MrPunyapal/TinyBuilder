"""Generate a small original grounded-answer pilot; no model access or training."""
import argparse
import hashlib
import json
from pathlib import Path
import random

SCHEMA = "tinybuilder-grounded-pilot-v1"
# Task families are deliberately disjoint across splits. These are public
# diagnostic examples, not secret release evaluation.
FAMILIES = {
    "train": ("route_handler", "python_default", "rust_flag"),
    "dev": ("queue_retry",),
    "eval": ("dependency_alias", "typescript_port"),
}
def row(family, rng, i):
    tag = f"demo_{rng.randrange(10**8):08d}"
    n = rng.randrange(2, 40)
    controller = rng.choice(("OrdersController", "AccountController", "SearchController"))
    method = rng.choice(("index", "show", "lookup"))
    boolean = rng.choice(("true", "false"))
    package = rng.choice(("example-parser", "example-reader", "example-codec"))
    if family == "route_handler":
        source = f"// routes.php\nRoute::get('/{tag}', [{controller}::class, '{method}']);\n"
        question = f"Which controller method handles GET /{tag}? Return Class::method only."
        answer = f"{controller}::{method}"
    elif family == "python_default":
        source = f"# settings.py\ndef connect_{tag}(timeout={n}):\n    return timeout\n"
        question = f"What is connect_{tag}'s default timeout? Return only the integer."
        answer = str(n)
    elif family == "rust_flag":
        flag = f"{tag}_enabled"
        source = f"// flags.rs\nstruct Flags {{ {flag}: bool }}\nfn defaults() -> Flags {{ Flags {{ {flag}: {boolean} }} }}\n"
        question = f"Is {flag} true or false by default? Return only the boolean."
        answer = boolean
    elif family == "queue_retry":
        source = f"# worker.toml\n[queues.{tag}]\nmax_attempts = {n}\nbackoff = 1\n"
        question = f"What is max_attempts for {tag}? Return only the integer."
        answer = str(n)
    elif family == "dependency_alias":
        source = f"# Cargo.toml\n[dependencies]\n{tag} = {{ package = \"{package}\", version = \"{n}.0\" }}\n"
        question = f"Which upstream package is aliased as {tag}? Return only the package name."
        answer = package
    elif family == "typescript_port":
        source = f"// config.ts\nexport const services = {{ {tag}: {{ port: {8000+n} }} }};\n"
        question = f"What port is configured for {tag}? Return only the integer."
        answer = str(8000+n)
    else:
        raise ValueError("Unknown family")
    return {"id":f"{family}-{i:04d}","family":family,"provenance":"original synthetic fixture",
        "instruction":question,"input":source,"output":answer}

def build(seed, per_family):
    if not 1 <= per_family <= 1000:
        raise ValueError("Invalid per-family count")
    rng=random.Random(seed)
    rows={split:[row(family,rng,i) for family in families for i in range(per_family)]
          for split,families in FAMILIES.items()}
    fingerprints=set()
    for split,items in rows.items():
        for item in items:
            key=hashlib.sha256((item["instruction"]+"\0"+item["input"]).encode()).hexdigest()
            if key in fingerprints:
                raise ValueError("Duplicate fixture")
            fingerprints.add(key)
    return rows

def export(output,seed,per_family):
    rows=build(seed,per_family)
    output.mkdir(exist_ok=False)
    reports={}
    for split,items in rows.items():
        # Keep governance metadata separate from the trainer input.
        dataset=[{k:r[k] for k in ("instruction","input","output")} for r in items]
        raw="".join(json.dumps(r,sort_keys=True)+"\n" for r in dataset).encode()
        (output/f"{split}.jsonl").write_bytes(raw)
        metadata="".join(json.dumps({k:r[k] for k in ("id","family","provenance")},sort_keys=True)+"\n" for r in items).encode()
        (output/f"{split}.provenance.jsonl").write_bytes(metadata)
        reports[split]={"rows":len(items),"families":list(FAMILIES[split]),
            "sha256":hashlib.sha256(raw).hexdigest(),"provenance_sha256":hashlib.sha256(metadata).hexdigest()}
    (output/"manifest.json").write_text(json.dumps({"schema":SCHEMA,"seed":seed,"per_family":per_family,
        "public_pilot_only":True,"training_authorized":False,"splits":reports},indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return reports

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--seed",type=int,default=20261126)
    p.add_argument("--per-family",type=int,default=20)
    a=p.parse_args()
    print(json.dumps(export(a.output,a.seed,a.per_family),indent=2))
