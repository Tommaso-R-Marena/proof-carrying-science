use certir::{BinOp, CmpOp, Expr, UnOp, Width};
use certir_interpreter::{eval_expr, eval_expr_checked, EvalError, Value};
use std::collections::HashMap;

fn main() {
    let variable = Expr::Var { name: "x".into() };
    let mut checks = 0;
    let canonical_error =
        || EvalError::Runtime("noncanonical bitvector input; use Value::bitvec".into());
    for width in [Width::U8, Width::U16, Width::U32, Width::U64] {
        for bits in [0, 1, width.mask()] {
            let value = Value::BitVec { width, bits };
            let store = HashMap::from([("x".into(), value)]);
            assert_eq!(eval_expr_checked(&store, &variable), Ok(value));
            checks += 1;
        }
        let shifted = Expr::BinOp {
            op: BinOp::Shl,
            lhs: Box::new(Expr::ConstBv { width, value: 1 }),
            rhs: Box::new(Expr::ConstBv {
                width,
                value: u64::from(width.bits()),
            }),
        };
        assert_eq!(
            eval_expr_checked(&HashMap::new(), &shifted),
            Ok(Value::bitvec(width, 0))
        );
        checks += 1;
        let mismatched = Expr::BinOp {
            op: BinOp::Add,
            lhs: Box::new(Expr::ConstBool { value: false }),
            rhs: Box::new(Expr::ConstBv { width, value: 0 }),
        };
        assert_eq!(
            eval_expr_checked(&HashMap::new(), &mismatched),
            eval_expr(&HashMap::new(), &mismatched)
        );
        assert!(eval_expr_checked(&HashMap::new(), &mismatched).is_err());
        checks += 1;
        if width != Width::U64 {
            let malformed = Value::BitVec {
                width,
                bits: 1u64 << width.bits(),
            };
            let store = HashMap::from([("x".into(), malformed)]);
            assert_eq!(eval_expr_checked(&store, &variable), Err(canonical_error()));
            checks += 1;
            let unused = HashMap::from([("unused".into(), malformed)]);
            assert_eq!(
                eval_expr_checked(&unused, &Expr::ConstBool { value: true }),
                Err(canonical_error())
            );
            checks += 1;
        }
    }
    let empty = HashMap::new();
    assert_eq!(
        eval_expr_checked(&empty, &variable),
        Err(EvalError::UndefinedVar("x".into()))
    );
    checks += 1;
    let bad_unop = Expr::UnOp {
        op: UnOp::Neg,
        expr: Box::new(Expr::ConstBool { value: true }),
    };
    assert_eq!(
        eval_expr_checked(&empty, &bad_unop),
        Err(EvalError::Runtime("bad unop".into()))
    );
    checks += 1;
    let bad_select = Expr::Select {
        cond: Box::new(Expr::ConstBv {
            width: Width::U8,
            value: 1,
        }),
        then_expr: Box::new(Expr::ConstBool { value: true }),
        else_expr: Box::new(Expr::ConstBool { value: false }),
    };
    assert_eq!(
        eval_expr_checked(&empty, &bad_select),
        Err(EvalError::Runtime("select cond not bool".into()))
    );
    checks += 1;
    let bool_order = Expr::Cmp {
        op: CmpOp::Ult,
        lhs: Box::new(Expr::ConstBool { value: false }),
        rhs: Box::new(Expr::ConstBool { value: true }),
    };
    assert!(eval_expr_checked(&empty, &bool_order).is_err());
    checks += 1;
    let bool_store = HashMap::from([("x".into(), Value::Bool(false))]);
    assert_eq!(
        eval_expr_checked(&bool_store, &variable),
        Ok(Value::Bool(false))
    );
    checks += 1;
    assert_eq!(checks, 31);
    println!("{{\"checks\":31,\"widths\":4,\"failed\":0}}");
}
