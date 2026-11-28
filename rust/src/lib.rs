pub mod agent;
pub mod grounded;
pub mod workbench;
pub mod multi_edit;
pub mod context;
pub mod project;
mod process;
mod loopback;
pub mod runtime;

pub fn terminal(text: &str) -> String {
    text.chars()
        .map(|c| if c.is_control() || matches!(c, '\u{202a}'..='\u{202e}' | '\u{2066}'..='\u{2069}' | '\u{200e}' | '\u{200f}') {
            c.escape_unicode().to_string()
        } else { c.to_string() })
        .collect()
}

pub fn show(text: &str) {
    for line in text.split('\n') {
        println!("| {}", terminal(line));
    }
}
