use clap::{Parser, Subcommand};
use pcs_independent_jcs::{canonicalize, jcs_sha256_hex, parse_rejecting_duplicates, sha256_bytes_hex};
use std::fs;
use std::path::PathBuf;
use std::process::ExitCode;

#[derive(Parser)]
#[command(name = "pcs-independent-jcs", about = "Independent JCS/SHA-256 checker for PCS evaluation")]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Canonicalize a JSON file and print RFC8785-ish text
    Canonicalize { path: PathBuf },
    /// Print SHA-256 of canonical JCS bytes
    Hash { path: PathBuf },
    /// Print SHA-256 of raw file bytes
    Sha256File { path: PathBuf },
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Canonicalize { path } => match fs::read_to_string(&path) {
            Ok(raw) => match parse_rejecting_duplicates(&raw) {
                Ok(v) => match canonicalize(&v) {
                    Ok(text) => {
                        println!("{text}");
                        ExitCode::SUCCESS
                    }
                    Err(e) => {
                        eprintln!("ERROR: {e}");
                        ExitCode::from(2)
                    }
                },
                Err(e) => {
                    eprintln!("ERROR: {e}");
                    ExitCode::from(2)
                }
            },
            Err(e) => {
                eprintln!("ERROR: {e}");
                ExitCode::from(2)
            }
        },
        Cmd::Hash { path } => match fs::read_to_string(&path) {
            Ok(raw) => match parse_rejecting_duplicates(&raw) {
                Ok(v) => match jcs_sha256_hex(&v) {
                    Ok(h) => {
                        println!("{h}");
                        ExitCode::SUCCESS
                    }
                    Err(e) => {
                        eprintln!("ERROR: {e}");
                        ExitCode::from(2)
                    }
                },
                Err(e) => {
                    eprintln!("ERROR: {e}");
                    ExitCode::from(2)
                }
            },
            Err(e) => {
                eprintln!("ERROR: {e}");
                ExitCode::from(2)
            }
        },
        Cmd::Sha256File { path } => match fs::read(&path) {
            Ok(raw) => {
                println!("{}", sha256_bytes_hex(&raw));
                ExitCode::SUCCESS
            }
            Err(e) => {
                eprintln!("ERROR: {e}");
                ExitCode::from(2)
            }
        },
    }
}
