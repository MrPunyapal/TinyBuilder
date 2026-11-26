//! Owned native runtime process. Model text never reaches shell syntax.
use anyhow::{Context, Result};
use std::{path::Path, process::{Child, Command, ExitStatus, Stdio}};

#[cfg(unix)]
const SUPERVISOR: &str = r#"
cleanup() {
    trap '' TERM INT HUP USR1
    kill -TERM 0
    /bin/sleep 1
    kill -KILL 0
}
trap cleanup TERM INT HUP USR1
(
    "$@" </dev/null >/dev/null 2>/dev/null
    kill -USR1 "$$"
) </dev/null &
IFS= read -r ignored || :
cleanup
"#;

pub fn command(exe: &Path) -> Command {
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        let mut cmd = Command::new("/bin/sh");
        cmd.args(["-c", SUPERVISOR, "tinybuilder-runtime"]).arg(exe);
        cmd.process_group(0);
        cmd
    }
    #[cfg(windows)]
    { Command::new(exe) }
}

pub struct Owned {
    child: Child,
    #[cfg(windows)]
    job: windows::Job,
}

impl Owned {
    pub fn spawn(command: &mut Command) -> Result<Self> {
        command.stdout(Stdio::null()).stderr(Stdio::null());
        #[cfg(unix)]
        command.stdin(Stdio::piped());
        #[cfg(windows)]
        command.stdin(Stdio::null());
        #[cfg(windows)]
        let job = windows::Job::new()?;
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            // No runtime instructions execute before job ownership is set.
            command.creation_flags(0x00000004); // CREATE_SUSPENDED
        }
        let mut_child = command.spawn().context("Owned runtime spawn failed")?;
        #[cfg(windows)]
        let mut mut_child = mut_child;
        #[cfg(windows)]
        if let Err(error) = job.attach(&mut_child).and_then(|_| windows::resume_primary(&mut_child)) {
            let _ = mut_child.kill();
            let _ = mut_child.wait();
            return Err(error);
        }
        Ok(Self { child: mut_child, #[cfg(windows)] job })
    }
    /// Confirm the IPv4 loopback listener belongs to the owned process/group.
    /// This is a point-in-time check, not atomic binding to an HTTP connection.
    pub fn listener_owned(&self, port: u16) -> Result<bool> {
        listener_owned(self.child.id(), port)
    }
    /// Identify the server-side established IPv4 tuple for this exact socket.
    /// No credentials or project data should be sent before this check succeeds.
    pub fn connection_owned(&self, socket: &std::net::TcpStream) -> Result<bool> {
        use std::net::{IpAddr, Ipv4Addr};
        let client = socket.local_addr()?;
        let server = socket.peer_addr()?;
        if client.ip()!=IpAddr::V4(Ipv4Addr::LOCALHOST)
            || server.ip()!=IpAddr::V4(Ipv4Addr::LOCALHOST)
            || client.port()==server.port() {return Ok(false);}
        connection_owned(self.child.id(),server.port(),client.port())
    }
    pub fn try_wait(&mut self) -> std::io::Result<Option<ExitStatus>> {
        self.child.try_wait()
    }
}

impl Drop for Owned {
    fn drop(&mut self) {
        #[cfg(windows)]
        {
            use std::{thread, time::{Duration, Instant}};
            self.job.terminate_and_close();
            let deadline = Instant::now() + Duration::from_secs(5);
            loop {
                match self.child.try_wait() {
                    Ok(Some(_)) => break,
                    Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(25)),
                    _ => { eprintln!("Runtime job cleanup not confirmed."); break; }
                }
            }
        }
        #[cfg(unix)]
        {
            use std::{thread, time::{Duration, Instant}};
            // EOF on parent death triggers cleanup from inside the still-owned
            // process group. Never signal a group by a potentially recycled PID.
            drop(self.child.stdin.take());
            let deadline = Instant::now() + Duration::from_secs(5);
            loop {
                match self.child.try_wait() {
                    Ok(Some(_)) => return,
                    Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(25)),
                    _ => {
                        eprintln!("Runtime supervisor cleanup not confirmed.");
                        return;
                    }
                }
            }
        }
    }
}


#[cfg(unix)]
fn in_group(pid: u32, group: u32) -> bool {
    extern "C" { fn getpgid(pid: i32) -> i32; }
    pid > 0 && pid <= i32::MAX as u32 && unsafe { getpgid(pid as i32) } == group as i32
}

#[cfg(target_os = "linux")]
fn listener_owned(group: u32, port: u16) -> Result<bool> {
    use std::{collections::BTreeSet, fs};
    let address = format!("0100007F:{port:04X}");
    let wildcard = format!("00000000:{port:04X}");
    let table = fs::read_to_string("/proc/net/tcp")?;
    let mut inodes = BTreeSet::new();
    for line in table.lines().skip(1) {
        let cols: Vec<_> = line.split_whitespace().collect();
        if cols.len() < 10 || cols[3] != "0A" { continue; }
        if cols[1] == wildcard { return Ok(false); }
        if cols[1] == address { inodes.insert(format!("socket:[{}]", cols[9])); }
    }
    if inodes.len() != 1 { return Ok(false); }
    let expected = inodes.iter().next().unwrap();
    for entry in fs::read_dir("/proc")? {
        let Ok(entry) = entry else { continue; };
        let Some(pid) = entry.file_name().to_str().and_then(|n| n.parse::<u32>().ok()) else { continue; };
        if !in_group(pid, group) { continue; }
        let Ok(fds) = fs::read_dir(entry.path().join("fd")) else { continue; };
        for fd in fds.flatten() {
            if fs::read_link(fd.path()).ok().as_deref() == Some(Path::new(expected)) {
                return Ok(in_group(pid, group));
            }
        }
    }
    Ok(false)
}

#[cfg(target_os = "linux")]
fn connection_owned(group: u32, server: u16, client: u16) -> Result<bool> {
    use std::{collections::BTreeSet, fs};
    let local=format!("0100007F:{server:04X}");
    let remote=format!("0100007F:{client:04X}");
    let mut inodes=BTreeSet::new();
    for line in fs::read_to_string("/proc/net/tcp")?.lines().skip(1) {
        let c:Vec<_>=line.split_whitespace().collect();
        if c.len()>=10 && c[1]==local && c[2]==remote && c[3]=="01" && c[9]!="0" {
            inodes.insert(format!("socket:[{}]",c[9]));
        }
    }
    if inodes.len()!=1 {return Ok(false);}
    let expected=inodes.iter().next().unwrap();
    for entry in fs::read_dir("/proc")? {
        let Ok(entry)=entry else {continue;};
        let Some(pid)=entry.file_name().to_str().and_then(|v|v.parse::<u32>().ok()) else {continue;};
        if !in_group(pid,group){continue;}
        let Ok(fds)=fs::read_dir(entry.path().join("fd")) else {continue;};
        for fd in fds.flatten() {
            if fs::read_link(fd.path()).ok().as_deref()==Some(Path::new(expected)) {
                return Ok(in_group(pid,group));
            }
        }
    }
    Ok(false)
}

#[cfg(target_os = "macos")]
fn connection_owned(group:u32,server:u16,client:u16)->Result<bool>{
    let out=Command::new("/usr/sbin/lsof").env_clear().env("PATH","/usr/bin:/bin")
        .args(["-nP","-a","-sTCP:ESTABLISHED","-Fpfn"])
        .arg(format!("-i4TCP:{server}"))
        .stdin(Stdio::null()).stderr(Stdio::null()).output()?;
    if !out.status.success(){return Ok(false);}
    let endpoint=format!("127.0.0.1:{server}->127.0.0.1:{client}");
    let mut pid=None;
    let mut matched=false;
    for line in std::str::from_utf8(&out.stdout)?.lines(){
        if let Some(value)=line.strip_prefix('p'){pid=value.parse::<u32>().ok();}
        else if line.strip_prefix('n')==Some(endpoint.as_str()){
            if matched||!pid.is_some_and(|p|in_group(p,group)){return Ok(false);}
            matched=true;
        }
    }
    Ok(matched)
}

#[cfg(windows)]
fn connection_owned(pid:u32,server:u16,client:u16)->Result<bool>{
    windows::connection_owned(pid,server,client)
}

#[cfg(target_os = "macos")]
fn listener_owned(group: u32, port: u16) -> Result<bool> {
    // lsof is supplied by macOS. No shell, user-controlled flags or PATH.
    let output = Command::new("/usr/sbin/lsof")
        .env_clear().env("PATH", "/usr/bin:/bin")
        .args(["-nP", "-a", "-sTCP:LISTEN", "-Fpfn"])
        .arg(format!("-i4TCP:{port}"))
        .stdin(Stdio::null()).stderr(Stdio::null()).output()?;
    if !output.status.success() { return Ok(false); }
    let result = std::str::from_utf8(&output.stdout)?;
    let mut owned = false;
    let mut pid_ok = false;
    let address = format!("127.0.0.1:{port}");
    for line in result.lines() {
        if let Some(pid) = line.strip_prefix('p') {
            pid_ok = pid.parse::<u32>().ok().is_some_and(|pid| in_group(pid, group));
            if !pid_ok { return Ok(false); }
        } else if let Some(name) = line.strip_prefix('n') {
            if !pid_ok || name != address { return Ok(false); }
            owned = true;
        }
    }
    Ok(owned)
}

#[cfg(windows)]
fn listener_owned(pid: u32, port: u16) -> Result<bool> {
    windows::listener_owned(pid, port)
}

#[cfg(windows)]
mod windows {
    use anyhow::{ensure, Result};
    use std::{ffi::c_void, mem::size_of, os::windows::io::AsRawHandle, process::Child, ptr};

    type Handle = *mut c_void;
    #[repr(C)]
    #[derive(Default)]
    struct Basic {
        per_process: i64, per_job: i64, flags: u32,
        min_ws: usize, max_ws: usize, active: u32, affinity: usize,
        priority: u32, scheduling: u32,
    }
    #[repr(C)]
    #[derive(Default)]
    struct Extended {
        basic: Basic, io: [u64; 6], process_memory: usize,
        job_memory: usize, peak_process: usize, peak_job: usize,
    }
    #[link(name = "kernel32")]
    extern "system" {
        fn CreateJobObjectW(attributes: *mut c_void, name: *const u16) -> Handle;
        fn SetInformationJobObject(job: Handle, class: i32, info: *const c_void, len: u32) -> i32;
        fn AssignProcessToJobObject(job: Handle, process: Handle) -> i32;
        fn TerminateJobObject(job: Handle, code: u32) -> i32;
        fn CloseHandle(handle: Handle) -> i32;
        fn CreateToolhelp32Snapshot(flags: u32, pid: u32) -> Handle;
        fn Thread32First(snapshot: Handle, entry: *mut ThreadEntry) -> i32;
        fn Thread32Next(snapshot: Handle, entry: *mut ThreadEntry) -> i32;
        fn OpenThread(access: u32, inherit: i32, thread_id: u32) -> Handle;
        fn ResumeThread(thread: Handle) -> u32;
    }
    #[repr(C)]
    struct ThreadEntry {
        size: u32, usage: u32, thread: u32, owner: u32,
        priority: i32, delta: i32, flags: u32,
    }
    struct ScopedHandle(Handle);
    impl Drop for ScopedHandle {
        fn drop(&mut self) { unsafe { CloseHandle(self.0); } }
    }
    pub fn resume_primary(child: &Child) -> Result<()> {
        let raw = unsafe { CreateToolhelp32Snapshot(4, 0) }; // TH32CS_SNAPTHREAD
        ensure!(raw as isize != -1, "Thread snapshot failed");
        let snapshot = ScopedHandle(raw);
        let mut entry = ThreadEntry { size: size_of::<ThreadEntry>() as u32,
            usage: 0, thread: 0, owner: 0, priority: 0, delta: 0, flags: 0 };
        ensure!(unsafe { Thread32First(snapshot.0, &mut entry) } != 0, "Thread enumeration failed");
        let mut primary = None;
        loop {
            if entry.owner == child.id() {
                ensure!(primary.is_none(), "Unexpected additional suspended process thread");
                primary = Some(entry.thread);
            }
            entry.size = size_of::<ThreadEntry>() as u32;
            if unsafe { Thread32Next(snapshot.0, &mut entry) } == 0 { break; }
        }
        let id = primary.ok_or_else(|| anyhow::anyhow!("Suspended primary thread unavailable"))?;
        let raw = unsafe { OpenThread(0x0002, 0, id) }; // THREAD_SUSPEND_RESUME
        ensure!(!raw.is_null(), "Primary thread open failed");
        let thread = ScopedHandle(raw);
        ensure!(unsafe { ResumeThread(thread.0) } == 1, "Primary thread resume failed");
        Ok(())
    }
    #[link(name = "iphlpapi")]
    extern "system" {
        fn GetExtendedTcpTable(table: *mut c_void, size: *mut u32, order: i32,
            family: u32, class: u32, reserved: u32) -> u32;
    }
    pub fn listener_owned(pid: u32, port: u16) -> Result<bool> {
        let mut bytes = 0u32;
        let rc = unsafe { GetExtendedTcpTable(ptr::null_mut(), &mut bytes, 0, 2, 3, 0) };
        ensure!(rc == 122 && (4..=16*1024*1024).contains(&bytes), "TCP table size unavailable");
        let mut words = vec![0u32; (bytes as usize + 3) / 4];
        let rc = unsafe { GetExtendedTcpTable(words.as_mut_ptr().cast(), &mut bytes, 0, 2, 3, 0) };
        if rc == 122 { return Ok(false); }
        ensure!(rc == 0 && bytes >= 4 && bytes as usize <= words.len()*4, "TCP table unavailable");
        let count = words[0] as usize;
        ensure!(count <= (bytes as usize / 4 - 1) / 6, "Malformed TCP table");
        let address = u32::from_ne_bytes([127, 0, 0, 1]);
        let mut owned = false;
        for row in words[1..1+count*6].chunks_exact(6) {
            if row[0] != 2 || u16::from_be(row[2] as u16) != port { continue; }
            if row[1] == 0 { return Ok(false); }
            if row[1] == address {
                if owned || row[5] != pid { return Ok(false); }
                owned = true;
            }
        }
        Ok(owned)
    }

    pub fn connection_owned(pid:u32,server:u16,client:u16)->Result<bool>{
        let mut bytes=0u32;
        // TCP_TABLE_OWNER_PID_ALL includes the established server-side row.
        let rc=unsafe{GetExtendedTcpTable(ptr::null_mut(),&mut bytes,0,2,5,0)};
        ensure!(rc==122&&(4..=16*1024*1024).contains(&bytes),"TCP table size unavailable");
        let mut words=vec![0u32;(bytes as usize+3)/4];
        let rc=unsafe{GetExtendedTcpTable(words.as_mut_ptr().cast(),&mut bytes,0,2,5,0)};
        if rc==122{return Ok(false);}
        ensure!(rc==0&&bytes>=4&&bytes as usize<=words.len()*4,"TCP table unavailable");
        let count=words[0] as usize;
        ensure!(count<=(bytes as usize/4-1)/6,"Malformed TCP table");
        let address=u32::from_ne_bytes([127,0,0,1]);
        let mut matched=false;
        for row in words[1..1+count*6].chunks_exact(6){
            if row[0]!=5||row[1]!=address||row[3]!=address
                ||u16::from_be(row[2] as u16)!=server||u16::from_be(row[4] as u16)!=client{continue;}
            if matched||row[5]!=pid{return Ok(false);}
            matched=true;
        }
        Ok(matched)
    }

    pub struct Job(Handle);
    impl Job {
        pub fn new() -> Result<Self> {
            let handle = unsafe { CreateJobObjectW(ptr::null_mut(), ptr::null()) };
            ensure!(!handle.is_null(), "Job creation failed");
            let job = Self(handle);
            let mut limits = Extended::default();
            limits.basic.flags = 0x2000; // KILL_ON_JOB_CLOSE
            ensure!(unsafe { SetInformationJobObject(handle, 9, &limits as *const _ as *const c_void, size_of::<Extended>() as u32) } != 0,
                "Job configuration failed");
            Ok(job)
        }
        pub fn attach(&self, child: &Child) -> Result<()> {
            // Exact process handle, while the primary thread is suspended.
            ensure!(unsafe { AssignProcessToJobObject(self.0, child.as_raw_handle()) } != 0, "Job assignment failed");
            Ok(())
        }
        pub fn terminate_and_close(&mut self) {
            if unsafe { TerminateJobObject(self.0, 1) } == 0 {
                eprintln!("Runtime job termination not confirmed; handle close will retry.");
            }
            // Closing the last job handle invokes KILL_ON_JOB_CLOSE. Do this
            // before waiting so a failed TerminateJobObject cannot hang exit.
            if unsafe { CloseHandle(self.0) } != 0 {
                self.0 = ptr::null_mut();
            } else {
                eprintln!("Runtime job handle close not confirmed.");
            }
        }
    }
    impl Drop for Job {
        fn drop(&mut self) {
            if !self.0.is_null() { unsafe { CloseHandle(self.0); } }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{fs, thread, time::{Duration, Instant}};
    #[test]
    fn listener_helper() {
        let Some(path) = std::env::var_os("TB_TEST_LISTENER") else { return; };
        let listener = std::net::TcpListener::bind(("127.0.0.1", 0)).unwrap();
        fs::write(path, listener.local_addr().unwrap().port().to_string()).unwrap();
        let (_socket, _) = listener.accept().unwrap();
        loop { thread::sleep(Duration::from_millis(100)); }
    }

    #[test]
    fn listener_identity_accepts_owned_and_rejects_foreign() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("port");
        let foreign = std::net::TcpListener::bind(("127.0.0.1", 0)).unwrap();
        let exe = std::env::current_exe().unwrap();
        let mut cmd = command(&exe);
        cmd.args(["--exact", "process::tests::listener_helper"])
            .env("TB_TEST_LISTENER", &file);
        let mut owned = Owned::spawn(&mut cmd).unwrap();
        let deadline = Instant::now() + Duration::from_secs(8);
        let port = loop {
            if let Ok(value) = fs::read_to_string(&file) {
                if let Ok(port) = value.parse::<u16>() { break port; }
            }
            assert!(Instant::now() < deadline, "Owned listener did not start");
            assert!(owned.try_wait().unwrap().is_none());
            thread::sleep(Duration::from_millis(30));
        };
        assert!(owned.listener_owned(port).unwrap(), "Owned listener not identified");
        assert!(!owned.listener_owned(foreign.local_addr().unwrap().port()).unwrap(),
            "Foreign listener accepted");
        let connection=std::net::TcpStream::connect(("127.0.0.1",port)).unwrap();
        let foreign_connection=std::net::TcpStream::connect(foreign.local_addr().unwrap()).unwrap();
        let (_foreign_server,_)=foreign.accept().unwrap();
        let deadline=Instant::now()+Duration::from_secs(5);
        while !owned.connection_owned(&connection).unwrap(){
            assert!(Instant::now()<deadline,"Owned connected socket not identified");
            thread::sleep(Duration::from_millis(30));
        }
        assert!(!owned.connection_owned(&foreign_connection).unwrap(),"Foreign established socket accepted");
    }

    // A test subprocess is the heartbeat producer, not an inference server.
    #[test]
    fn heartbeat_helper() {
        let Some(path) = std::env::var_os("TB_TEST_HEARTBEAT") else { return; };
        use std::io::Write;
        let mut f = fs::OpenOptions::new().create(true).append(true).open(path).unwrap();
        loop {
            f.write_all(b"x").unwrap();
            f.flush().unwrap();
            thread::sleep(Duration::from_millis(30));
        }
    }
    #[test]
    fn parent_helper() {
        let Some(path) = std::env::var_os("TB_TEST_PARENT") else { return; };
        let exe = std::env::current_exe().unwrap();
        let mut cmd = command(&exe);
        cmd.args(["--exact", "process::tests::heartbeat_helper"])
            .env_remove("TB_TEST_PARENT").env("TB_TEST_HEARTBEAT", &path);
        let _owned = Owned::spawn(&mut cmd).unwrap();
        let deadline = Instant::now() + Duration::from_secs(8);
        while Instant::now() < deadline {
            if fs::metadata(&path).map(|m| m.len() >= 3).unwrap_or(false) {
                // Deliberately bypass Drop, exercising parent-death ownership.
                std::process::exit(0);
            }
            thread::sleep(Duration::from_millis(40));
        }
        panic!("Heartbeat did not start");
    }
    #[test]
    fn abrupt_parent_exit_stops_heartbeat() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("heartbeat");
        let mut parent = Command::new(std::env::current_exe().unwrap())
            .args(["--exact", "process::tests::parent_helper"])
            .env_remove("TB_TEST_HEARTBEAT").env("TB_TEST_PARENT", &file)
            .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).spawn().unwrap();
        let deadline = Instant::now() + Duration::from_secs(12);
        loop {
            if let Some(status) = parent.try_wait().unwrap() { assert!(status.success()); break; }
            if Instant::now() >= deadline {
                let _ = parent.kill(); let _ = parent.wait();
                panic!("Parent helper timeout");
            }
            thread::sleep(Duration::from_millis(40));
        }
        thread::sleep(Duration::from_millis(1700));
        let size = fs::metadata(&file).unwrap().len();
        assert!(size >= 3);
        thread::sleep(Duration::from_millis(300));
        assert_eq!(fs::metadata(file).unwrap().len(), size);
    }
}
