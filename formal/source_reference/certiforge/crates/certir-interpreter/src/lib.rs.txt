//! Executable CertIR semantics — must stay aligned with Lean `eval`.

use certir::{BinOp, CmpOp, Expr, Program, Ty, UnOp, Width};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Value {
    Bool(bool),
    BitVec { width: Width, bits: u64 },
}

impl Value {
    pub fn bitvec(width: Width, bits: u64) -> Self {
        Value::BitVec {
            width,
            bits: bits & width.mask(),
        }
    }

    pub fn ty(self) -> Ty {
        match self {
            Value::Bool(_) => Ty::Bool,
            Value::BitVec { width, .. } => Ty::BitVec(width),
        }
    }
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum EvalError {
    #[error("undefined variable `{0}`")]
    UndefinedVar(String),
    #[error("type/runtime error: {0}")]
    Runtime(String),
    #[error("arity mismatch: expected {expected} inputs, got {got}")]
    Arity { expected: usize, got: usize },
}

fn eval_binop(op: BinOp, width: Width, a: u64, b: u64) -> u64 {
    let mask = width.mask();
    let a = a & mask;
    let b = b & mask;
    let r = match op {
        BinOp::Add => a.wrapping_add(b),
        BinOp::Sub => a.wrapping_sub(b),
        BinOp::Mul => a.wrapping_mul(b),
        BinOp::And => a & b,
        BinOp::Or => a | b,
        BinOp::Xor => a ^ b,
        BinOp::Shl => {
            if b >= u64::from(width.bits()) {
                0
            } else {
                a << b
            }
        }
        BinOp::Lshr => {
            if b >= u64::from(width.bits()) {
                0
            } else {
                a >> b
            }
        }
    };
    r & mask
}

fn eval_cmp_bv(op: CmpOp, a: u64, b: u64) -> bool {
    match op {
        CmpOp::Eq => a == b,
        CmpOp::Ne => a != b,
        CmpOp::Ult => a < b,
        CmpOp::Ule => a <= b,
        CmpOp::Ugt => a > b,
        CmpOp::Uge => a >= b,
    }
}

pub fn eval_expr(store: &HashMap<String, Value>, expr: &Expr) -> Result<Value, EvalError> {
    match expr {
        Expr::ConstBool { value } => Ok(Value::Bool(*value)),
        Expr::ConstBv { width, value } => Ok(Value::bitvec(*width, *value)),
        Expr::Var { name } => store
            .get(name)
            .copied()
            .ok_or_else(|| EvalError::UndefinedVar(name.clone())),
        Expr::UnOp { op, expr } => {
            let v = eval_expr(store, expr)?;
            match (op, v) {
                (UnOp::Not, Value::Bool(b)) => Ok(Value::Bool(!b)),
                (UnOp::Not, Value::BitVec { width, bits }) => Ok(Value::bitvec(width, !bits)),
                (UnOp::Neg, Value::BitVec { width, bits }) => {
                    Ok(Value::bitvec(width, bits.wrapping_neg()))
                }
                _ => Err(EvalError::Runtime("bad unop".into())),
            }
        }
        Expr::BinOp { op, lhs, rhs } => {
            let l = eval_expr(store, lhs)?;
            let r = eval_expr(store, rhs)?;
            match (l, r) {
                (Value::BitVec { width: w1, bits: a }, Value::BitVec { width: w2, bits: b })
                    if w1 == w2 =>
                {
                    Ok(Value::bitvec(w1, eval_binop(*op, w1, a, b)))
                }
                _ => Err(EvalError::Runtime("bad binop".into())),
            }
        }
        Expr::Cmp { op, lhs, rhs } => {
            let l = eval_expr(store, lhs)?;
            let r = eval_expr(store, rhs)?;
            match (l, r) {
                (Value::BitVec { width: w1, bits: a }, Value::BitVec { width: w2, bits: b })
                    if w1 == w2 =>
                {
                    Ok(Value::Bool(eval_cmp_bv(*op, a, b)))
                }
                (Value::Bool(a), Value::Bool(b)) => match op {
                    CmpOp::Eq => Ok(Value::Bool(a == b)),
                    CmpOp::Ne => Ok(Value::Bool(a != b)),
                    _ => Err(EvalError::Runtime("bad bool cmp".into())),
                },
                _ => Err(EvalError::Runtime("bad cmp".into())),
            }
        }
        Expr::Select {
            cond,
            then_expr,
            else_expr,
        } => match eval_expr(store, cond)? {
            Value::Bool(true) => eval_expr(store, then_expr),
            Value::Bool(false) => eval_expr(store, else_expr),
            _ => Err(EvalError::Runtime("select cond not bool".into())),
        },
    }
}

pub fn eval(program: &Program, inputs: &[Value]) -> Result<Value, EvalError> {
    if inputs.len() != program.params.len() {
        return Err(EvalError::Arity {
            expected: program.params.len(),
            got: inputs.len(),
        });
    }
    let mut store = HashMap::new();
    for (param, val) in program.params.iter().zip(inputs.iter()) {
        if param.ty != val.ty() {
            return Err(EvalError::Runtime(format!(
                "input type mismatch for {}: expected {}, got {:?}",
                param.name,
                param.ty,
                val.ty()
            )));
        }
        store.insert(param.name.clone(), *val);
    }
    let out = eval_expr(&store, &program.body)?;
    if out.ty() != program.ret_ty {
        return Err(EvalError::Runtime("return type mismatch".into()));
    }
    Ok(out)
}

/// Observational equivalence on a finite input sample.
pub fn observationally_equal(
    p: &Program,
    q: &Program,
    samples: &[Vec<Value>],
) -> Result<bool, EvalError> {
    for inputs in samples {
        match (eval(p, inputs), eval(q, inputs)) {
            (Ok(a), Ok(b)) if a == b => {}
            (Ok(_), Ok(_)) => return Ok(false),
            (Err(_), Err(_)) => {}
            _ => return Ok(false),
        }
    }
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    use certir_parser::parse_program;

    #[test]
    fn and_xor_eq_or() {
        let p = parse_program("fn p(x: u32, y: u32) -> u32 { add(and(x, y), xor(x, y)) }").unwrap();
        let q = parse_program("fn q(x: u32, y: u32) -> u32 { or(x, y) }").unwrap();
        let samples = vec![
            vec![Value::bitvec(Width::U32, 0), Value::bitvec(Width::U32, 0)],
            vec![Value::bitvec(Width::U32, 1), Value::bitvec(Width::U32, 2)],
            vec![
                Value::bitvec(Width::U32, 0xFFFF_FFFF),
                Value::bitvec(Width::U32, 0x1234_5678),
            ],
        ];
        assert!(observationally_equal(&p, &q, &samples).unwrap());
    }

    #[test]
    fn wrapping_add() {
        let p = parse_program("fn p(x: u8) -> u8 { add(x, u8(1)) }").unwrap();
        let v = eval(&p, &[Value::bitvec(Width::U8, 255)]).unwrap();
        assert_eq!(v, Value::bitvec(Width::U8, 0));
    }

    #[test]
    fn reject_bad_opt() {
        let p = parse_program("fn p(x: u32) -> u32 { add(x, x) }").unwrap();
        let bad = parse_program("fn q(x: u32) -> u32 { x }").unwrap();
        let samples = vec![vec![Value::bitvec(Width::U32, 1)]];
        assert!(!observationally_equal(&p, &bad, &samples).unwrap());
    }

    #[test]
    fn large_u64_shift_does_not_truncate_to_u32() {
        for op in ["shl", "lshr"] {
            let p = parse_program(&format!(
                "fn p(x: u64) -> u64 {{ {op}(x, u64(4294967296)) }}"
            ))
            .unwrap();
            assert_eq!(
                eval(&p, &[Value::bitvec(Width::U64, 7)]).unwrap(),
                Value::bitvec(Width::U64, 0)
            );
        }
    }
}
