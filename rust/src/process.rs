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
        let mut_child = command.spawn().context("Owned runtime spawn failed")?;
        #[cfg(windows)]
        let mut mut_child = mut_child;
        #[cfg(windows)]
        if let Err(error) = job.attach(&mut_child) {
            let _ = mut_child.kill();
            let _ = mut_child.wait();
            return Err(error);
        }
        Ok(Self { child: mut_child, #[cfg(windows)] job })
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
            // Exact process handle, never reopen a PID. Trusted server starts
            // before assignment; suspended-spawn parity remains a hardening gate.
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
