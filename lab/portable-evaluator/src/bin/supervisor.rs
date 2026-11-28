use tinybuilder_portable_evaluator::supervisor::{run_suite, sibling_worker};
fn main() {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.len() != 1 || args[0] != "trusted-suite" {
        eprintln!("usage: portable-evaluator-supervisor trusted-suite");
        std::process::exit(2);
    }
    let result = sibling_worker().and_then(|worker| run_suite(&worker));
    match result {
        Ok(record) => {
            if serde_json::to_writer_pretty(std::io::stdout().lock(), &record).is_err() {
                std::process::exit(2);
            }
            if !record.all_controls_passed { std::process::exit(1); }
        }
        Err(_) => { eprintln!("trusted-control setup blocked"); std::process::exit(2); }
    }
}
