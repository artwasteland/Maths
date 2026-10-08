"""Size reduction by elementary, exactly verified Koszul syzygies."""
def count(cert):return sum(len(p.to_dict()) for p in cert.values())

def reduce_cofactors(cert,gens,reverse=False):
    out=dict(cert)
    keys=sorted(gens,key=lambda k:(0 if k.startswith("s:") else 1,k)) if reverse else list(gens)
    zero=next(iter(gens.values())).context().constant(0)
    for i,k in enumerate(keys):
        p=out.get(k,zero)
        if not p:continue
        for j in keys[i+1:]:
            q,p=divmod(p,gens[j])
            if q:
                out[j]=out.get(j,zero)+q*gens[k]
        if p:out[k]=p
        else:out.pop(k,None)
    return {k:p for k,p in out.items() if p}
