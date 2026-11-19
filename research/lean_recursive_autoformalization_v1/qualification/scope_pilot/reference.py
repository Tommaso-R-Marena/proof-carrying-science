"""Extensional reference written as set relations before the model call."""
def denotations(tagged, inspected, universe):
    return dict(
        a=tagged <= inspected, b=inspected <= tagged, c=bool(tagged & inspected),
        d=bool(tagged - inspected), e=tagged.isdisjoint(inspected), f=bool(inspected - tagged),
        g=(tagged | inspected) == universe, h=tagged != universe,
        i=not tagged or bool(inspected), j=(tagged & inspected) == universe,
        k=bool(universe - (tagged | inspected)), l=tagged == inspected)
