//! Existing, trusted installed llama.cpp runtime. No downloads or remote API.
use anyhow::{bail, ensure, Context, Result};
use crate::process::{self, Owned};
use rand::{distributions::Alphanumeric, Rng};
use serde::Deserialize;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::{self, File},
    io::Read,
    net::TcpListener,
    path::{Path, PathBuf},
    thread,
    time::{Duration, Instant},
};

// Published official release asset digests; not local archive/build qualification.
fn pin(revision: &str) -> Result<(&'static str, &'static str, &'static str, &'static str)> {
    match (revision, std::env::consts::OS, std::env::consts::ARCH) {
        ("b12359", "windows", "x86_64") => Ok(("windows", "x64", "llama-b12359-bin-win-cpu-x64.zip",
            "837c1655e87df3b66989f4be33a792a1399c785bf259038dc75c900096683e69")),
        ("b12359", "macos", "aarch64") => Ok(("macos", "arm64", "llama-b12359-bin-macos-arm64.tar.gz",
            "82b00abc740160e1b9980e6cc79c117345fa34af058c80e6c0a69aa8ddccde75")),
        ("b12359", "linux", "x86_64") => Ok(("linux", "x64", "llama-b12359-bin-ubuntu-x64.tar.gz",
            "0bc1f091e8916102b6d8f2cf944233a620e90a0f856c72d0ce41150c65c2e72e")),
        ("b6500", "windows", "x86_64") => Ok(("windows", "x64", "llama-b6500-bin-win-cpu-x64.zip",
            "73e00267e852e666a6fce2c3fb7a2603dd1934a37259f3f45c2c1b6983fa605a")),
        ("b6500", "macos", "aarch64") => Ok(("macos", "arm64", "llama-b6500-bin-macos-arm64.zip",
            "4f34ae19823ee22e8036d6da91f083ca62ab926c2a0a4a5ce9df34897360087b")),
        ("b6500", "linux", "x86_64") => Ok(("linux", "x64", "llama-b6500-bin-ubuntu-x64.zip",
            "716803084e565fe779bc2d01ea576c418be141f8fabac97509bc6d7c3cd786b2")),
        _ => bail!("Unsupported runtime platform"),
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Manifest {
    schema: u32,
    revision: String,
    os: String,
    architecture: String,
    backend: String,
    executable: String,
    archive: String,
    archive_sha256: String,
    native_dependencies: Vec<String>,
    files: BTreeMap<String, String>,
}
fn regular(path: &Path) -> Result<()> {
    let meta = path.symlink_metadata()?;
    ensure!(meta.is_file() && !meta.file_type().is_symlink(), "Non-regular runtime file");
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        ensure!(meta.file_attributes() & 0x400 == 0, "Runtime reparse point");
    }
    Ok(())
}
fn digest(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut hash = Sha256::new();
    let mut buf = [0u8; 64 * 1024];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 { break; }
        hash.update(&buf[..n]);
    }
    Ok(format!("{:x}", hash.finalize()))
}
fn valid_name(name: &str) -> bool {
    !name.is_empty() && name.len() <= 128 && !name.starts_with('.') && !name.ends_with('.')
        && name.bytes().all(|b| b.is_ascii_alphanumeric() || b"_.+-".contains(&b))
        && ![".gguf", ".safetensors", ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".env"].iter().any(|s| name.to_ascii_lowercase().ends_with(s))
}
pub fn verify_runtime(root: &Path) -> Result<PathBuf> {
    ensure!(root.is_absolute(), "Use an absolute trusted runtime directory");
    let root_meta = root.symlink_metadata()?;
    ensure!(root_meta.is_dir() && !root_meta.file_type().is_symlink(), "Runtime root must be a real directory");
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        ensure!(root_meta.file_attributes() & 0x400 == 0, "Runtime root reparse point");
    }
    let root = root.canonicalize()?;
    let manifest_path = root.join("runtime-manifest.json");
    regular(&manifest_path)?;
    ensure!(manifest_path.metadata()?.len() <= 1024 * 1024, "Oversized runtime manifest");
    let data: Manifest = serde_json::from_reader(File::open(manifest_path)?)?;
    let (os, arch, archive, sha) = pin(&data.revision)?;
    let exe = if os == "windows" { "llama-server.exe" } else { "llama-server" };
    ensure!(data.schema == 1 && data.os == os
        && data.architecture == arch && data.backend == "cpu" && data.executable == exe
        && data.archive == archive && data.archive_sha256 == sha, "Runtime manifest pin mismatch");
    ensure!(data.files.contains_key(exe) && data.files.contains_key("LICENSE"), "Missing runtime files");
    let deps: BTreeSet<_> = data.native_dependencies.iter().collect();
    ensure!(deps.len() == data.native_dependencies.len() && data.native_dependencies.iter().all(|n| n != exe && n != "LICENSE" && data.files.contains_key(n)), "Invalid dependency inventory");
    let mut names = BTreeSet::new();
    let mut folded = BTreeSet::new();
    for entry in fs::read_dir(&root)? {
        let entry = entry?;
        regular(&entry.path())?;
        let name = entry.file_name().into_string().map_err(|_| anyhow::anyhow!("Invalid runtime filename"))?;
        ensure!(folded.insert(name.to_ascii_lowercase()), "Duplicate runtime path");
        names.insert(name);
    }
    let mut expected: BTreeSet<_> = data.files.keys().cloned().collect();
    expected.insert("runtime-manifest.json".into());
    ensure!(names == expected && data.files.len() <= 256, "Runtime inventory mismatch");
    for (name, expected) in data.files {
        ensure!(valid_name(&name) && name != "runtime-manifest.json", "Invalid runtime filename");
        ensure!(digest(&root.join(name))? == expected, "Runtime digest mismatch");
    }
    Ok(root.join(exe))
}

pub fn model_path(path: &Path) -> Result<PathBuf> {
    let path = path.canonicalize().context("Model unavailable")?;
    regular(&path)?;
    ensure!(path.extension().and_then(|s| s.to_str()).is_some_and(|s| s.eq_ignore_ascii_case("gguf")), "Select a GGUF file");
    let mut header = [0u8; 8];
    File::open(&path)?.read_exact(&mut header)?;
    ensure!(&header[..4] == b"GGUF", "Invalid GGUF header");
    Ok(path)
}

pub struct Runtime {
    child: Owned,
    base: String,
    alias: String,
    key: String,
}
fn client(timeout: Duration) -> ureq::Agent {
    // No proxy-from-env feature and no redirects. Managed URLs are constructed
    // internally and are never sourced from model or project text.
    ureq::AgentBuilder::new().redirects(0).timeout(timeout).build()
}
fn bounded_json(response: ureq::Response) -> Result<Value> {
    let mut buf = Vec::new();
    response.into_reader().take(2 * 1024 * 1024 + 1).read_to_end(&mut buf)?;
    ensure!(buf.len() <= 2 * 1024 * 1024, "Response too large");
    serde_json::from_slice(&buf).map_err(|_| anyhow::anyhow!("Invalid server JSON"))
}
fn status(result: std::result::Result<ureq::Response, ureq::Error>) -> Option<u16> {
    match result {
        Ok(r) => Some(r.status()),
        Err(ureq::Error::Status(code, _)) => Some(code),
        _ => None,
    }
}

impl Runtime {
    pub fn start(root: &Path, model: &Path) -> Result<Self> {
        let exe = verify_runtime(root)?;
        let model = model_path(model)?;
        let socket = TcpListener::bind(("127.0.0.1", 0))?;
        let port = socket.local_addr()?.port();
        drop(socket);
        let key: String = rand::thread_rng().sample_iter(&Alphanumeric).take(48).map(char::from).collect();
        let alias: String = format!("tinybuilder-{}", rand::thread_rng().sample_iter(&Alphanumeric).take(24).map(char::from).collect::<String>());
        let dir = exe.parent().context("Missing runtime directory")?;
        let mut command = process::command(&exe);
        command.current_dir(dir).env_clear().env("LLAMA_API_KEY", &key)
            .args(["--model"]).arg(&model)
            .args(["--host", "127.0.0.1", "--port"]).arg(port.to_string())
            .args(["--alias", &alias, "--device", "none", "--n-gpu-layers", "0", "--no-webui", "--no-slots", "--jinja", "--log-disable"]);
        #[cfg(windows)]
        {
            let system = std::env::var_os("SystemRoot").context("SystemRoot missing")?;
            let path = std::env::join_paths([dir.to_owned(), PathBuf::from(&system).join("System32")])?;
            command.env("SystemRoot", &system).env("WINDIR", &system).env("PATH", path);
        }
        #[cfg(unix)]
        command.env("PATH", "/usr/bin:/bin");
        #[cfg(target_os = "linux")]
        command.env("LD_LIBRARY_PATH", dir);
        let child = Owned::spawn(&mut command).map_err(|_| anyhow::anyhow!("Runtime spawn failed"))?;
        let mut runtime = Self { child, base: format!("http://127.0.0.1:{port}"), alias, key };
        runtime.ready()?;
        Ok(runtime)
    }
    fn ready(&mut self) -> Result<()> {
        let end = Instant::now() + Duration::from_secs(180);
        let http = client(Duration::from_millis(500));
        while Instant::now() < end {
            ensure!(self.child.try_wait()?.is_none(), "Runtime exited before readiness");
            match status(http.get(&format!("{}/health", self.base)).call()) {
                Some(200) => {
                    let url = format!("{}/props", self.base);
                    ensure!(matches!(status(http.get(&url).call()), Some(401 | 403)), "Runtime accepted missing authentication");
                    ensure!(matches!(status(http.get(&url).set("Authorization", "Bearer invalid-session").call()), Some(401 | 403)), "Runtime accepted invalid authentication");
                    ensure!(status(http.get(&url).set("Authorization", &format!("Bearer {}", self.key)).call()) == Some(200), "Runtime authentication failed");
                    // b12359 protects /v1/models; b6500 accepts authenticated
                    // access too. Require the random session alias after auth.
                    let models = http.get(&format!("{}/v1/models", self.base))
                        .set("Authorization", &format!("Bearer {}", self.key)).call()
                        .map_err(|_| anyhow::anyhow!("Runtime identity probe failed"))?;
                    let data = bounded_json(models)?;
                    ensure!(data["data"].as_array().is_some_and(|rows| rows.iter().any(|r| r["id"].as_str() == Some(self.alias.as_str()))), "Runtime identity mismatch");
                    ensure!(self.child.try_wait()?.is_none(), "Runtime exited during readiness");
                    return Ok(());
                }
                None | Some(503) => thread::sleep(Duration::from_millis(100)),
                _ => bail!("Unexpected runtime readiness response"),
            }
        }
        bail!("Runtime startup timed out")
    }
    /// Plain-text SSE only; never stream tool calls or constrained actions.
    pub fn stream_answer(&self, mut payload:Value, emit:impl FnMut(&str)->Result<()>) -> Result<String> {
        ensure!(payload.get("tools").is_none() && payload.get("response_format").is_none(),"Streaming is plain-answer only");
        payload["model"]=Value::String(self.alias.clone());
        payload["stream"]=Value::Bool(true);
        let response=client(Duration::from_secs(120))
            .post(&format!("{}/v1/chat/completions",self.base))
            .set("Authorization",&format!("Bearer {}",self.key))
            .send_json(payload).map_err(|_|anyhow::anyhow!("Local stream request failed"))?;
        ensure!(response.header("Content-Type").is_some_and(|v|v.split(';').next()==Some("text/event-stream")),"Unexpected stream content type");
        crate::stream::read_answer(response.into_reader(),emit)
    }
    pub fn complete(&self, mut payload: Value) -> Result<Value> {
        payload["model"] = Value::String(self.alias.clone());
        let response = client(Duration::from_secs(120))
            .post(&format!("{}/v1/chat/completions", self.base))
            .set("Authorization", &format!("Bearer {}", self.key))
            .send_json(payload)
            .map_err(|err| match err {
                ureq::Error::Status(code, _) => anyhow::anyhow!("Model HTTP status {code}"),
                _ => anyhow::anyhow!("Local model transport failed"),
            })?;
        let response = bounded_json(response)?;
        let choice = &response["choices"][0];
        ensure!(matches!(choice["finish_reason"].as_str(), Some("stop" | "tool_calls")), "Incomplete model response");
        ensure!(choice["message"].is_object(), "Missing model message");
        Ok(choice["message"].clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn approved_pin_and_inventory_only() {
        for revision in ["b6500", "b12359"] {
            let dir = tempfile::tempdir().unwrap();
            let root = dir.path();
            let (os, arch, archive, sha) = pin(revision).unwrap();
            let exe = if os == "windows" { "llama-server.exe" } else { "llama-server" };
            fs::write(root.join(exe), b"fixture, never executed").unwrap();
            fs::write(root.join("LICENSE"), b"fixture license").unwrap();
            let files = BTreeMap::from([(exe, digest(&root.join(exe)).unwrap()), ("LICENSE", digest(&root.join("LICENSE")).unwrap())]);
            let manifest = serde_json::json!({"schema":1,"revision":revision,"os":os,"architecture":arch,
                "backend":"cpu","executable":exe,"archive":archive,"archive_sha256":sha,
                "native_dependencies":[],"files":files});
            let path = root.join("runtime-manifest.json");
            fs::write(&path, serde_json::to_vec(&manifest).unwrap()).unwrap();
            assert_eq!(verify_runtime(root).unwrap(), root.canonicalize().unwrap().join(exe));
            let mut wrong = manifest.clone();
            wrong["revision"] = serde_json::json!("unknown");
            fs::write(&path, serde_json::to_vec(&wrong).unwrap()).unwrap();
            assert!(verify_runtime(root).is_err());
            fs::write(&path, serde_json::to_vec(&manifest).unwrap()).unwrap();
            fs::write(root.join(exe), b"changed").unwrap();
            assert!(verify_runtime(root).is_err());
        }
    }
}
