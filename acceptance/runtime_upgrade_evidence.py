"""Inspect official patched runtime candidate archives, never execute or extract."""
import hashlib
import json
import argparse
from pathlib import Path
import re
import tarfile
import tempfile
from runtime_evidence import download, inspect, MAX_ARCHIVE, MAX_EXPANDED

REVISION="b12359"
SOURCE_COMMIT="b1b770d90d94cad9e9ea5b993bdbc383a522fb28"
PINS={
    "windows":("llama-b12359-bin-win-cpu-x64.zip","837c1655e87df3b66989f4be33a792a1399c785bf259038dc75c900096683e69"),
    "macos":("llama-b12359-bin-macos-arm64.tar.gz","82b00abc740160e1b9980e6cc79c117345fa34af058c80e6c0a69aa8ddccde75"),
    "linux":("llama-b12359-bin-ubuntu-x64.tar.gz","0bc1f091e8916102b6d8f2cf944233a620e90a0f856c72d0ce41150c65c2e72e"),
}
def inspect_tar(path,expected):
    if path.stat().st_size>MAX_ARCHIVE:
        raise ValueError("Archive exceeds limit")
    with path.open("rb") as file:
        if hashlib.file_digest(file,"sha256").hexdigest()!=expected:
            raise ValueError("Archive digest mismatch")
    rows=[]
    seen=set()
    count=total=0
    with tarfile.open(path,"r|gz") as archive:
        for member in archive:
            count+=1
            total+=member.size
            if count>10000 or total>MAX_EXPANDED:
                raise ValueError("Archive inventory exceeds limit")
            name=member.name.rstrip("/")
            if (not re.fullmatch(r"[A-Za-z0-9_./+ -]+",name)
                or any(p in {"",".",".."} for p in name.split("/"))
                or name.casefold() in seen):
                raise ValueError("Unsafe or duplicate member")
            seen.add(name.casefold())
            if member.isdir():
                continue
            if member.issym() or member.islnk():
                rows.append({"path":name,"kind":"symlink" if member.issym() else "hardlink","target":member.linkname,"bytes":member.size})
                continue
            if not member.isreg() or member.issparse():
                raise ValueError("Unsupported member")
            stream=archive.extractfile(member)
            if stream is None:
                raise ValueError("Missing member data")
            sha=hashlib.sha256()
            remaining=member.size
            while block:=stream.read(1024*1024):
                remaining-=len(block)
                sha.update(block)
            if remaining:
                raise ValueError("Truncated member")
            rows.append({"path":name,"kind":"regular","bytes":member.size,"sha256":sha.hexdigest()})
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("target",choices=PINS)
    a=p.parse_args()
    name,sha=PINS[a.target]
    url=f"https://github.com/ggml-org/llama.cpp/releases/download/{REVISION}/{name}"
    with tempfile.TemporaryDirectory() as tmp:
        file=Path(tmp)/name
        size=download(url,file,sha)
        rows=inspect(file,sha) if name.endswith(".zip") else inspect_tar(file,sha)
        server="llama-server.exe" if a.target=="windows" else "llama-server"
        if sum(r["path"].split("/")[-1]==server and r["kind"]=="regular" for r in rows)!=1:
            raise ValueError("Missing unique server")
        print(json.dumps({"revision":REVISION,"source_commit":SOURCE_COMMIT,"target":a.target,
            "archive_sha256":sha,"archive_bytes":size,"source":url,"members":rows,
            "status":"input evidence only; no runtime or model execution"},indent=2))
if __name__=="__main__":
    main()
