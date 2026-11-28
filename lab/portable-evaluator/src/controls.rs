//! Reviewed, fixed WAT controls. No file, source, module or argv admission.
use crate::Probe;

pub fn source(probe: Probe) -> &'static str {
    match probe {
        Probe::Return42 => r#"(module (func (export "observe") (result i32) i32.const 42))"#,
        Probe::NoPreopen => r#"(module
          (import "wasi_snapshot_preview1" "fd_prestat_get" (func $get (param i32 i32) (result i32)))
          (memory (export "memory") 1)
          (func (export "observe") (result i32) i32.const 3 i32.const 0 call $get))"#,
        Probe::NoPath => r#"(module
          (import "wasi_snapshot_preview1" "path_open" (func $open (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32)))
          (memory (export "memory") 1)
          (data (i32.const 16) "../canary")
          (func (export "observe") (result i32)
            i32.const 3 i32.const 0 i32.const 16 i32.const 9 i32.const 0
            i64.const 2 i64.const 0 i32.const 0 i32.const 0 call $open))"#,
        Probe::NoEnvironment => r#"(module
          (import "wasi_snapshot_preview1" "environ_sizes_get" (func $get (param i32 i32) (result i32)))
          (memory (export "memory") 1)
          (func (export "observe") (result i32)
            i32.const 0 i32.const 4 call $get
            if (result i32) i32.const -1 else
              i32.const 0 i32.load i32.const 4 i32.load i32.or
            end))"#,
        Probe::NoArguments => r#"(module
          (import "wasi_snapshot_preview1" "args_sizes_get" (func $get (param i32 i32) (result i32)))
          (memory (export "memory") 1)
          (func (export "observe") (result i32)
            i32.const 0 i32.const 4 call $get
            if (result i32) i32.const -1 else
              i32.const 0 i32.load i32.const 4 i32.load i32.or
            end))"#,
        Probe::NoSocket => r#"(module
          (import "wasi_snapshot_preview1" "sock_accept" (func $accept (param i32 i32 i32) (result i32)))
          (memory (export "memory") 1)
          (func (export "observe") (result i32) i32.const 3 i32.const 0 i32.const 0 call $accept))"#,
        Probe::NoHostSpawn => r#"(module
          (import "tinybuilder_host" "spawn" (func $spawn))
          (func (export "observe") (result i32) call $spawn i32.const 0))"#,
        Probe::MemoryAllowed => r#"(module
          (memory 1)
          (func (export "observe") (result i32) i32.const 1 memory.grow))"#,
        Probe::MemoryDenied => r#"(module
          (memory 1)
          (func (export "observe") (result i32) i32.const 2 memory.grow))"#,
        Probe::Fuel => r#"(module
          (func (export "observe") (result i32)
            (loop $again br $again) i32.const 0))"#,
        Probe::Epoch => r#"(module
          (func (export "observe") (result i32)
            (loop $again br $again) i32.const 0))"#,
        // Native watchdog control: no guest, no child, no host access.
        Probe::Watchdog => "native-watchdog-ready-then-sleep-30s-v1",
    }
}
