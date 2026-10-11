//! CertIR v0 — pure straight-line fixed-width bitvector IR.
//!
//! Lean definitions in `formal/CertiForge/` are the canonical semantics.
//! This crate is an executable twin, differential-tested against Lean.

use serde::{Deserialize, Serialize};
use std::fmt;
use thiserror::Error;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Width {
    U8,
    U16,
    U32,
    U64,
}

impl Width {
    pub fn bits(self) -> u32 {
        match self {
            Width::U8 => 8,
            Width::U16 => 16,
            Width::U32 => 32,
            Width::U64 => 64,
        }
    }

    pub fn mask(self) -> u64 {
        if self.bits() == 64 {
            u64::MAX
        } else {
            (1u64 << self.bits()) - 1
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "u8" => Some(Width::U8),
            "u16" => Some(Width::U16),
            "u32" => Some(Width::U32),
            "u64" => Some(Width::U64),
            _ => None,
        }
    }
}

impl fmt::Display for Width {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Width::U8 => write!(f, "u8"),
            Width::U16 => write!(f, "u16"),
            Width::U32 => write!(f, "u32"),
            Width::U64 => write!(f, "u64"),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Ty {
    Bool,
    BitVec(Width),
}

impl fmt::Display for Ty {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Ty::Bool => write!(f, "bool"),
            Ty::BitVec(w) => write!(f, "{w}"),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum BinOp {
    Add,
    Sub,
    Mul,
    And,
    Or,
    Xor,
    Shl,
    Lshr,
}

impl BinOp {
    pub fn as_str(self) -> &'static str {
        match self {
            BinOp::Add => "add",
            BinOp::Sub => "sub",
            BinOp::Mul => "mul",
            BinOp::And => "and",
            BinOp::Or => "or",
            BinOp::Xor => "xor",
            BinOp::Shl => "shl",
            BinOp::Lshr => "lshr",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "add" | "+" => Some(BinOp::Add),
            "sub" | "-" => Some(BinOp::Sub),
            "mul" | "*" => Some(BinOp::Mul),
            "and" | "&" => Some(BinOp::And),
            "or" | "|" => Some(BinOp::Or),
            "xor" | "^" => Some(BinOp::Xor),
            "shl" | "<<" => Some(BinOp::Shl),
            "lshr" | ">>" => Some(BinOp::Lshr),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CmpOp {
    Eq,
    Ne,
    Ult,
    Ule,
    Ugt,
    Uge,
}

impl CmpOp {
    pub fn as_str(self) -> &'static str {
        match self {
            CmpOp::Eq => "eq",
            CmpOp::Ne => "ne",
            CmpOp::Ult => "ult",
            CmpOp::Ule => "ule",
            CmpOp::Ugt => "ugt",
            CmpOp::Uge => "uge",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "eq" | "==" => Some(CmpOp::Eq),
            "ne" | "!=" => Some(CmpOp::Ne),
            "ult" | "<" => Some(CmpOp::Ult),
            "ule" | "<=" => Some(CmpOp::Ule),
            "ugt" | ">" => Some(CmpOp::Ugt),
            "uge" | ">=" => Some(CmpOp::Uge),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum UnOp {
    Not,
    Neg,
}

impl UnOp {
    pub fn as_str(self) -> &'static str {
        match self {
            UnOp::Not => "not",
            UnOp::Neg => "neg",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "not" | "!" | "~" => Some(UnOp::Not),
            "neg" => Some(UnOp::Neg),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Expr {
    ConstBool {
        value: bool,
    },
    ConstBv {
        width: Width,
        value: u64,
    },
    Var {
        name: String,
    },
    UnOp {
        op: UnOp,
        expr: Box<Expr>,
    },
    BinOp {
        op: BinOp,
        lhs: Box<Expr>,
        rhs: Box<Expr>,
    },
    Cmp {
        op: CmpOp,
        lhs: Box<Expr>,
        rhs: Box<Expr>,
    },
    Select {
        cond: Box<Expr>,
        then_expr: Box<Expr>,
        else_expr: Box<Expr>,
    },
}

impl Expr {
    pub fn node_count(&self) -> usize {
        match self {
            Expr::ConstBool { .. } | Expr::ConstBv { .. } | Expr::Var { .. } => 1,
            Expr::UnOp { expr, .. } => 1 + expr.node_count(),
            Expr::BinOp { lhs, rhs, .. } | Expr::Cmp { lhs, rhs, .. } => {
                1 + lhs.node_count() + rhs.node_count()
            }
            Expr::Select {
                cond,
                then_expr,
                else_expr,
            } => 1 + cond.node_count() + then_expr.node_count() + else_expr.node_count(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Param {
    pub name: String,
    pub ty: Ty,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Program {
    pub name: String,
    pub params: Vec<Param>,
    pub body: Expr,
    pub ret_ty: Ty,
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum TypeError {
    #[error("duplicate parameter `{0}`")]
    DuplicateParam(String),
    #[error("undefined variable `{0}`")]
    UndefinedVar(String),
    #[error("type mismatch: expected {expected}, got {got}")]
    Mismatch { expected: String, got: String },
    #[error("unsupported operand types for operator")]
    BadOperands,
}

pub type Env = Vec<(String, Ty)>;

pub fn lookup(env: &Env, name: &str) -> Option<Ty> {
    env.iter().rev().find(|(n, _)| n == name).map(|(_, t)| *t)
}

pub fn type_of(env: &Env, expr: &Expr) -> Result<Ty, TypeError> {
    match expr {
        Expr::ConstBool { .. } => Ok(Ty::Bool),
        Expr::ConstBv { width, .. } => Ok(Ty::BitVec(*width)),
        Expr::Var { name } => {
            lookup(env, name).ok_or_else(|| TypeError::UndefinedVar(name.clone()))
        }
        Expr::UnOp { op, expr } => {
            let t = type_of(env, expr)?;
            match (op, t) {
                (UnOp::Not, Ty::Bool) => Ok(Ty::Bool),
                (UnOp::Not, Ty::BitVec(w)) => Ok(Ty::BitVec(w)),
                (UnOp::Neg, Ty::BitVec(w)) => Ok(Ty::BitVec(w)),
                _ => Err(TypeError::BadOperands),
            }
        }
        Expr::BinOp { op: _, lhs, rhs } => {
            let tl = type_of(env, lhs)?;
            let tr = type_of(env, rhs)?;
            match (tl, tr) {
                (Ty::BitVec(w1), Ty::BitVec(w2)) if w1 == w2 => Ok(Ty::BitVec(w1)),
                _ => Err(TypeError::BadOperands),
            }
        }
        Expr::Cmp { lhs, rhs, .. } => {
            let tl = type_of(env, lhs)?;
            let tr = type_of(env, rhs)?;
            match (tl, tr) {
                (Ty::BitVec(w1), Ty::BitVec(w2)) if w1 == w2 => Ok(Ty::Bool),
                (Ty::Bool, Ty::Bool) => Ok(Ty::Bool),
                _ => Err(TypeError::BadOperands),
            }
        }
        Expr::Select {
            cond,
            then_expr,
            else_expr,
        } => {
            let tc = type_of(env, cond)?;
            if tc != Ty::Bool {
                return Err(TypeError::Mismatch {
                    expected: "bool".into(),
                    got: tc.to_string(),
                });
            }
            let tt = type_of(env, then_expr)?;
            let te = type_of(env, else_expr)?;
            if tt != te {
                return Err(TypeError::Mismatch {
                    expected: tt.to_string(),
                    got: te.to_string(),
                });
            }
            Ok(tt)
        }
    }
}

impl Program {
    pub fn env(&self) -> Env {
        self.params.iter().map(|p| (p.name.clone(), p.ty)).collect()
    }

    pub fn check(&self) -> Result<(), TypeError> {
        let mut names = std::collections::BTreeSet::new();
        for param in &self.params {
            if !names.insert(&param.name) {
                return Err(TypeError::DuplicateParam(param.name.clone()));
            }
        }
        let ty = type_of(&self.env(), &self.body)?;
        if ty != self.ret_ty {
            return Err(TypeError::Mismatch {
                expected: self.ret_ty.to_string(),
                got: ty.to_string(),
            });
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn well_typed_and_or_identity() {
        let p = Program {
            name: "or_via_add".into(),
            params: vec![
                Param {
                    name: "x".into(),
                    ty: Ty::BitVec(Width::U32),
                },
                Param {
                    name: "y".into(),
                    ty: Ty::BitVec(Width::U32),
                },
            ],
            body: Expr::BinOp {
                op: BinOp::Add,
                lhs: Box::new(Expr::BinOp {
                    op: BinOp::And,
                    lhs: Box::new(Expr::Var { name: "x".into() }),
                    rhs: Box::new(Expr::Var { name: "y".into() }),
                }),
                rhs: Box::new(Expr::BinOp {
                    op: BinOp::Xor,
                    lhs: Box::new(Expr::Var { name: "x".into() }),
                    rhs: Box::new(Expr::Var { name: "y".into() }),
                }),
            },
            ret_ty: Ty::BitVec(Width::U32),
        };
        assert!(p.check().is_ok());
    }
}
