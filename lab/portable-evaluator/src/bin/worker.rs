//! Trusted embedded controls only. No argv, file loading, module bytes or candidate inputs.
use std::{io, thread, time::Duration};
use std::io::Write;
use tinybuilder_portable_evaluator::{
    bounded_read, controls, BackendIdentity, Observation, Probe, Request, WorkerReply, WATCHDOG_READY,
};
use wasmtime::{Config, Engine, Linker, Module, Store, StoreLimits, StoreLimitsBuilder, Trap};
use wasmtime_wasi::{p1::{self, WasiP1Ctx}, WasiCtxBuilder};

struct State { wasi: WasiP1Ctx, limits: StoreLimits }

fn observe(request: &Request) -> Result<Observation, ()> {
    let mut config = Config::new();
    config.consume_fuel(true).epoch_interruption(true);
    let engine = Engine::new(&config).map_err(|_| ())?;
    let module = Module::new(&engine, controls::source(request.probe)).map_err(|_| ())?;
    let mut linker: Linker<State> = Linker::new(&engine);
    p1::add_to_linker_sync(&mut linker, |state| &mut state.wasi).map_err(|_| ())?;
    // No preopened dirs, inherited stdio, args, environment or network.
    let wasi = WasiCtxBuilder::new().build_p1();
    let l = request.limits;
    let limits = StoreLimitsBuilder::new().memory_size(l.memory_bytes)
        .table_elements(l.table_elements).instances(l.instances)
        .memories(l.memories).tables(l.tables).build();
    let mut store = Store::new(&engine, State { wasi, limits });
    store.limiter(|state| &mut state.limits);
    store.set_fuel(l.fuel).map_err(|_| ())?;
    store.set_epoch_deadline(1);
    store.epoch_deadline_trap();
    if request.probe == Probe::NoHostSpawn {
        // The exact unregistered import must be absent, and instantiation must fail.
        if linker.get(&mut store, "tinybuilder_host", "spawn").is_none()
            && linker.instantiate(&mut store, &module).is_err() {
            return Ok(Observation::ImportDenied);
        }
        return Err(());
    }
    let instance = linker.instantiate(&mut store, &module).map_err(|_| ())?;
    let observe = instance.get_typed_func::<(), i32>(&mut store, "observe").map_err(|_| ())?;
    // Deterministic epoch deadline probe: advance the epoch before entering the loop.
    if request.probe == Probe::Epoch { engine.increment_epoch(); }
    match observe.call(&mut store, ()) {
        Ok(value) => Ok(Observation::Returned(value)),
        Err(error) if matches!(error.downcast_ref::<Trap>(), Some(Trap::OutOfFuel)) => Ok(Observation::FuelExhausted),
        Err(error) if matches!(error.downcast_ref::<Trap>(), Some(Trap::Interrupt)) => Ok(Observation::EpochInterrupted),
        Err(_) => Err(()),
    }
}

fn run() -> Result<(), ()> {
    if std::env::args_os().len() != 1 { return Err(()); }
    let bytes = bounded_read(io::stdin().lock()).map_err(|_| ())?;
    let request: Request = serde_json::from_slice(&bytes).map_err(|_| ())?;
    let exe = std::env::current_exe().map_err(|_| ())?;
    let actual = BackendIdentity::for_worker(&exe).map_err(|_| ())?;
    request.validate(&actual).map_err(|_| ())?;
    if request.probe == Probe::Watchdog {
        let mut stdout = io::stdout().lock();
        stdout.write_all(WATCHDOG_READY).map_err(|_| ())?;
        stdout.flush().map_err(|_| ())?;
        drop(stdout);
        thread::sleep(Duration::from_secs(30));
        return Err(()); // A supervisor that doesn't kill this is broken.
    }
    let observation = observe(&request)?;
    serde_json::to_writer(io::stdout().lock(), &WorkerReply { request, observation }).map_err(|_| ())?;
    Ok(())
}

fn main() {
    // Never print untrusted diagnostics or guest data to the parent's terminal.
    if run().is_err() { std::process::exit(2); }
}
