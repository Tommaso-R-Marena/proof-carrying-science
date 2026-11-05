use certir::{BinOp, Expr, Param, Program, Ty, UnOp, Width};
use certir_interpreter::{eval, EvalError, Value};

fn program(body: Expr, ret_ty: Ty) -> Program {
    Program {
        name: "output_boundary_v3".into(),
        params: vec![],
        body,
        ret_ty,
    }
}

fn main() {
    let widths = [Width::U8, Width::U16, Width::U32, Width::U64];
    let types = [
        Ty::Bool,
        Ty::BitVec(Width::U8),
        Ty::BitVec(Width::U16),
        Ty::BitVec(Width::U32),
        Ty::BitVec(Width::U64),
    ];
    let mut checks = 0;
    for actual in types {
        for declared in types {
            let (body, value) = match actual {
                Ty::Bool => (Expr::ConstBool { value: true }, Value::Bool(true)),
                Ty::BitVec(width) => (
                    Expr::ConstBv {
                        width,
                        value: width.mask(),
                    },
                    Value::bitvec(width, width.mask()),
                ),
            };
            let result = eval(&program(body, declared), &[]);
            if actual == declared {
                assert_eq!(result, Ok(value));
            } else {
                assert_eq!(
                    result,
                    Err(EvalError::Runtime("return type mismatch".into()))
                );
            }
            checks += 1;
        }
    }
    let missing = program(
        Expr::Var {
            name: "missing".into(),
        },
        Ty::Bool,
    );
    assert_eq!(
        eval(&missing, &[]),
        Err(EvalError::UndefinedVar("missing".into()))
    );
    checks += 1;
    let unop = program(
        Expr::UnOp {
            op: UnOp::Neg,
            expr: Box::new(Expr::ConstBool { value: true }),
        },
        Ty::BitVec(Width::U8),
    );
    assert_eq!(eval(&unop, &[]), Err(EvalError::Runtime("bad unop".into())));
    checks += 1;
    let binop = program(
        Expr::BinOp {
            op: BinOp::Add,
            lhs: Box::new(Expr::ConstBool { value: true }),
            rhs: Box::new(Expr::ConstBool { value: false }),
        },
        Ty::Bool,
    );
    assert_eq!(
        eval(&binop, &[]),
        Err(EvalError::Runtime("bad binop".into()))
    );
    checks += 1;
    let select = program(
        Expr::Select {
            cond: Box::new(Expr::ConstBv {
                width: Width::U8,
                value: 1,
            }),
            then_expr: Box::new(Expr::ConstBool { value: true }),
            else_expr: Box::new(Expr::ConstBool { value: false }),
        },
        Ty::Bool,
    );
    assert_eq!(
        eval(&select, &[]),
        Err(EvalError::Runtime("select cond not bool".into()))
    );
    checks += 1;
    for width in [Width::U8, Width::U16, Width::U32] {
        let mut p = program(Expr::Var { name: "x".into() }, Ty::Bool);
        p.params.push(Param {
            name: "x".into(),
            ty: Ty::BitVec(width),
        });
        assert_eq!(
            eval(
                &p,
                &[Value::BitVec {
                    width,
                    bits: 1u64 << width.bits()
                }]
            ),
            Err(EvalError::Runtime(
                "noncanonical bitvector input; use Value::bitvec".into()
            ))
        );
        checks += 1;
    }
    let maximum = program(
        Expr::ConstBv {
            width: Width::U64,
            value: u64::MAX,
        },
        Ty::BitVec(Width::U64),
    );
    assert_eq!(eval(&maximum, &[]), Ok(Value::bitvec(Width::U64, u64::MAX)));
    checks += 1;
    let mut one_input = program(Expr::Var { name: "x".into() }, Ty::Bool);
    one_input.params.push(Param {
        name: "x".into(),
        ty: Ty::Bool,
    });
    assert_eq!(
        eval(&one_input, &[]),
        Err(EvalError::Arity {
            expected: 1,
            got: 0
        })
    );
    checks += 1;
    assert_eq!(
        eval(
            &program(Expr::ConstBool { value: true }, Ty::Bool),
            &[Value::Bool(false)]
        ),
        Err(EvalError::Arity {
            expected: 0,
            got: 1
        })
    );
    checks += 1;
    for width in widths {
        let mut p = program(Expr::Var { name: "x".into() }, Ty::BitVec(width));
        p.params.push(Param {
            name: "x".into(),
            ty: Ty::BitVec(width),
        });
        match eval(&p, &[Value::Bool(true)]) {
            Err(EvalError::Runtime(message)) => {
                assert!(message.starts_with("input type mismatch for x:"))
            }
            other => panic!("input mismatch was not rejected: {other:?}"),
        }
        checks += 1;
    }
    let dead_branch = program(
        Expr::Select {
            cond: Box::new(Expr::ConstBool { value: false }),
            then_expr: Box::new(Expr::Var {
                name: "missing".into(),
            }),
            else_expr: Box::new(Expr::ConstBool { value: true }),
        },
        Ty::Bool,
    );
    assert_eq!(eval(&dead_branch, &[]), Ok(Value::Bool(true)));
    checks += 1;
    assert_eq!(checks, 40);
    println!("{{\"checks\":40,\"type_pairs\":25,\"widths\":4,\"failed\":0}}");
}
