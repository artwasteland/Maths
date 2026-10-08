"""Reproduce the unaccepted index 39 derivation and its corruption control."""
from analytic39 import *
from ideal_derivation import verify_document
import copy

def main():
 configure();start=time.monotonic();doc=construct(forbidden_canonical()[39],[0,8],derivation_only=True)
 path=EVIDENCE/'39-ideal-derivation.json';path.write_text(json.dumps(doc,separators=(',',':'))+'\n');n=verify_document(doc)
 bad=copy.deepcopy(doc);k=next(iter(bad['rows'][0]['cofactors']));bad['rows'][0]['cofactors'][k][0][0]=str(fmpq(bad['rows'][0]['cofactors'][k][0][0])+1)
 try:verify_document(bad)
 except ValueError as e:assert str(e)=='proposal identity at row 0';reason=str(e)
 else:raise AssertionError('corruption accepted')
 result={'status':'local prototype only, not official acceptance','rows':n,'bytes':path.stat().st_size,'seconds':time.monotonic()-start,'one_coefficient_mutation':reason,'argv':sys.argv}
 (EVIDENCE/'39-ideal-derivation-test.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
