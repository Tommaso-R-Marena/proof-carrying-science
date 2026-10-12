//! Test-only adapter: invokes the actual selected CertiForge crates, without copying their evaluator.
use certir::{Program, TypeError, Width};
use certir_interpreter::{eval, EvalError, Value};
use serde_json::{json, Value as Json};
use std::io::{self, BufRead};

fn input(j: &Json) -> Value {
    if j["kind"] == "bool" {
        Value::Bool(j["value"].as_bool().expect("bool"))
    } else {
        // Deliberately construct the public enum directly: unmasked payloads are tested.
        let w: Width = serde_json::from_value(j["width"].clone()).expect("width");
        Value::BitVec { width: w, bits: j["bits"].as_u64().expect("u64") }
    }
}

fn value(v: Value) -> String {
    match v {
        Value::Bool(b) => format!("ok:bool:{b}"),
        Value::BitVec { width, bits } => format!("ok:bv:{}:{bits}", width.bits()),
    }
}

fn eval_error(e: EvalError) -> String {
    match e {
        EvalError::UndefinedVar(n) => format!("error:undefined:{n}"),
        EvalError::Arity { expected, got } => format!("error:arity:{expected}:{got}"),
        EvalError::Runtime(m) if m.starts_with("input type mismatch for ") => {
            // Lean's existing transcription abstracts the formatted type payload.
            let n = m.trim_start_matches("input type mismatch for ").split(':').next().unwrap();
            format!("error:input:{n}")
        }
        EvalError::Runtime(m) => format!("error:runtime:{m}"),
    }
}

fn check_error(e: TypeError) -> String {
    match e {
        TypeError::DuplicateParam(_) => "error:duplicate".into(),
        TypeError::UndefinedVar(n) => format!("error:undefined:{n}"),
        TypeError::Mismatch { .. } => "error:mismatch".into(),
        TypeError::BadOperands => "error:operands".into(),
    }
}

fn main() {
    for line in io::stdin().lock().lines() {
        let raw = line.expect("stdin");
        assert!(raw.len() <= 262144, "bounded test input");
        let j: Json = serde_json::from_str(&raw).expect("test JSON");
        let p: Program = serde_json::from_value(j["program"].clone()).expect("program");
        let inputs: Vec<Value> = j["inputs"].as_array().expect("inputs").iter().map(input).collect();
        let result = match eval(&p, &inputs) { Ok(v) => value(v), Err(e) => eval_error(e) };
        let check = match p.check() { Ok(()) => "ok".into(), Err(e) => check_error(e) };
        println!("{}", json!({"eval": result, "check": check}));
    }
}
