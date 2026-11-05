"""Bounded exact-Fraction reconstruction from an *untrusted* LP dual support.

Optional algebra for proof production; the verifier does not import this.
No floating-point solver status is proof. Recovered multipliers are always
rechecked against exact original constraints before being accepted.
"""
from fractions import Fraction
from .relational_kernel import cut,Unsupported


def recover(rows,goal,approx,*,threshold=1e-8):
    """Reconstruct an exact rational dual using the numerical support only.

    Solve A_support^T * lambda = goal with exact Gaussian elimination. Free
    variables set to zero; if this gives negative multipliers, abstain.
    """
    try:
        support=[k for k,q in enumerate(approx) if float(q)>threshold]
        if not support or len(support)>96 or len(goal)>512:return None
        # Dense rational elimination is limited; no trusted result on overflow.
        width=len(support)
        a=[]
        for j in range(len(goal)):
            a.append([cut(rows[ix][0].get(j,Fraction(0))) for ix in support]+[cut(goal[j])])
        r=0;pivots=[]
        for col in range(width):
            pick=next((i for i in range(r,len(a)) if a[i][col]),None)
            if pick is None:continue
            a[r],a[pick]=a[pick],a[r]
            factor=a[r][col]
            for j in range(col,width+1):a[r][j]=cut(a[r][j]/factor)
            for i in range(len(a)):
                if i==r or not a[i][col]:continue
                factor=a[i][col]
                for j in range(col,width+1):a[i][j]=cut(a[i][j]-factor*a[r][j])
            pivots.append((col,r));r+=1
            if r==len(a):break
        if any(not any(a[i][j] for j in range(width)) and a[i][width] for i in range(len(a))):return None
        solution=[Fraction(0)]*width
        for col,row in pivots:solution[col]=a[row][width]
        if any(x<0 for x in solution):return None
        nonzero={support[j]:q for j,q in enumerate(solution) if q>0}
        if not nonzero:return None
        # Exact identity verification: no faith in elimination or numerical LP.
        recovered=[Fraction(0)]*len(goal)
        for k,q in nonzero.items():
            for j,v in rows[k][0].items():recovered[j]=cut(recovered[j]+q*v)
        if recovered!=goal:return None
        return nonzero
    except (ArithmeticError,TypeError,ValueError,OverflowError,MemoryError,Unsupported):
        return None
