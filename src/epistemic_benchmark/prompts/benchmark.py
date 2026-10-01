from epistemic_benchmark.utils.io import require

def inventory(w):
    wid=w['world_id'];out=[]
    for c in range(1,9):
        for probe,task in [('P1','InitialState'),('P2','SourceProvenance')]:out.append(('T1',task,'C'+str(c),f'{wid}.CORE.C{c}.{probe}'))
    for profile in ('HH','LL','HL','LH'):
        for probe,task in [('P3c','RelativeReliability'),('P3a','ExactCountO1'),('P3b','ExactCountO2')]:out.append(('T1',task,profile,f'{wid}.R.{profile}.AB.NONE.{probe}'))
    for c in range(1,9):out.append(('T2','Factorial','C'+str(c),f'{wid}.CORE.C{c}.P4'))
    for profile in ('HL','LH'):out.append(('T3','ReliabilitySwap',profile,f'{wid}.R.{profile}.AB.NONE.P4'))
    for order in ('A_first','B_first'):
        for time in ('08:00','12:00'):out.append(('T4','TextTime',order+'.'+time,f'{wid}.T.{order}.{time}.P4'))
    for c in range(1,5):out.append(('T4','ReportStructure','S'+str(c),f'{wid}.C.C{c}.P4'))
    for truth in ('A','B'):out.append(('T5','Verified',truth,f'{wid}.VERIFIED_{truth}.D4'))
    require(len(out)==48,'Wrong benchmark inventory');return out
