"""Mechanical minimum A1 deliverable checks. Semantic validation remains a judge duty."""
import glob,os,re
from pathlib import Path

def check_a1_bundle(root):
    errors=[];docs={}
    for kind in ('SRS','REGISTER','VALIDATION'):
        paths=sorted(glob.glob(os.path.join(root,'.autose','artifacts',f'*_{kind}_v*.md')))
        if not paths:errors.append(f'missing versioned A1 {kind} artifact');continue
        docs[kind]=Path(paths[-1]).read_text(encoding='utf-8')
        if len(docs[kind].strip())<160:errors.append(f'A1 {kind} artifact is too short to contain required sections')
    expected={'SRS':['purpose','actors','constraints','functional requirements','non-functional','acceptance criteria','dependencies','traceability'],
              'REGISTER':['source statements','ambiguous','open questions','assumptions','conflicts','evidence','coverage','change log'],
              'VALIDATION':['verdict','gate','basis','tool','human']}
    for kind,terms in expected.items():
        text=docs.get(kind,'').lower()
        if not text:continue
        for term in terms:
            if term not in text:errors.append(f'{kind} missing required topic: {term}')
    val=docs.get('VALIDATION','')
    required=['C1','C2','C3','C4','K1','K2','K3','R-1','R-2','R-3','F1','F2','T1','T2','T3','T4','E1','E2','E3','E4','E5']
    for key in required:
        if not re.search(r'\b'+re.escape(key)+r'\b[^\n]*(?:PASS|FAIL|N/A)',val,re.I):
            errors.append(f'VALIDATION lacks explicit PASS/FAIL/N/A result for {key}')
    if not re.search(r'\b(?:READY|PARTIALLY READY|NOT READY)\b',val):errors.append('VALIDATION lacks readiness verdict')
    if docs.get('SRS') and not re.search(r'\bS-\d+',docs['SRS']):errors.append('SRS lacks source statement links')
    return not errors,errors,docs
