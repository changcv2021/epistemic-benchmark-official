"""Fixed L2 logistic comparisons using eight-cell sufficient statistics, no new dependency."""

import math

from collections import defaultdict

from epistemic_benchmark.utils.io import require

from epistemic_benchmark.prompts.factorial import CONDITIONS

from epistemic_benchmark.analysis.design import validate_folds

def features(condition,interactions):
    r,q,i=CONDITIONS[condition]
    r=.5 if r=='HH' else -.5;q=.5 if q=='high' else -.5;i=.5 if i=='distinct' else -.5
    return [1.,r,q,i]+([r*q,r*i,q*i,r*q*i] if interactions else [])

def sigmoid(x):
    if x>=0:return 1/(1+math.exp(-x))
    v=math.exp(x);return v/(1+v)

def softplus(x):return max(x,0)+math.log1p(math.exp(-abs(x)))

def solve(matrix,vector):
    n=len(vector);a=[list(row)+[v] for row,v in zip(matrix,vector)]
    for j in range(n):
        pivot=max(range(j,n),key=lambda k:abs(a[k][j]))
        if abs(a[pivot][j])<1e-14:raise ArithmeticError('Singular unpenalized-intercept Hessian')
        a[j],a[pivot]=a[pivot],a[j];scale=a[j][j]
        a[j]=[v/scale for v in a[j]]
        for k in range(n):
            if k!=j:
                scale=a[k][j];a[k]=[x-scale*y for x,y in zip(a[k],a[j])]
    return [row[-1] for row in a]

def fit(cells,interactions,max_iter=2000):
    """cells maps condition to (valid n, B choices); objective=sum loss + .5*L2, C=1."""
    n=sum(v[0] for v in cells.values());positive=sum(v[1] for v in cells.values())
    if not n or positive in (0,n):return dict(status='not_estimable_single_or_no_training_class',training_n=n,positive=positive)
    data=[(features(c,interactions),count,yes) for c,(count,yes) in cells.items() if count]
    width=8 if interactions else 4;beta=[0.]*width
    beta[0]=math.log(positive/(n-positive))
    def objective(b):
        total=.5*sum(v*v for v in b[1:])
        for x,count,yes in data:
            z=sum(a*v for a,v in zip(x,b));total+=count*softplus(z)-yes*z
        return total
    value=objective(beta)
    for iteration in range(max_iter):
        gradient=[0.]+beta[1:];hessian=[[float(i==j and i>0) for j in range(width)] for i in range(width)]
        for x,count,yes in data:
            p=sigmoid(sum(a*v for a,v in zip(x,beta)));residual=count*p-yes;weight=count*p*(1-p)
            for i in range(width):
                gradient[i]+=x[i]*residual
                for j in range(width):hessian[i][j]+=weight*x[i]*x[j]
        if max(abs(g) for g in gradient)<=1e-8:
            return dict(status='converged',beta=beta,iterations=iteration,objective=value,max_abs_gradient=max(abs(g) for g in gradient),training_n=n)
        try:step=solve(hessian,gradient)
        except ArithmeticError as exc:return dict(status='not_converged',reason=str(exc),iterations=iteration)
        scale=1.;descent=sum(g*s for g,s in zip(gradient,step));accepted=False
        for _ in range(60):
            candidate=[b-scale*s for b,s in zip(beta,step)];new_value=objective(candidate)
            if new_value<=value-1e-4*scale*descent+1e-12:
                beta=candidate;value=new_value;accepted=True;break
            scale*=.5
        if not accepted:return dict(status='not_converged',reason='line_search',iterations=iteration)
    return dict(status='not_converged',reason='iteration_limit',iterations=max_iter)

def evaluate(cells,model,interactions):
    n=sum(v[0] for v in cells.values())
    if not n or model['status']!='converged':return dict(n=n,log_loss=None,Brier=None)
    loss=brier=0.
    for c,(count,yes) in cells.items():
        z=sum(a*b for a,b in zip(features(c,interactions),model['beta']));p=sigmoid(z)
        loss+=count*softplus(z)-yes*z;brier+=yes*(1-p)**2+(count-yes)*p*p
    return dict(n=n,log_loss=loss/n,Brier=brier/n)

def compare(worlds,index,design):
    validate_folds(worlds,design);results={}
    subsets={'core':[w for w in worlds if w['split']=='core'],'all':worlds}
    for subset,selected in subsets.items():
        for grouping in ('world_grouped','renderer_grouped'):
            grouping_plan=design[grouping];fold_results=[]
            if grouping_plan['folds']<2:
                results[subset+'.'+grouping]=dict(status='not_estimable_fewer_than_two_groups');continue
            for fold in range(grouping_plan['folds']):
                train=defaultdict(lambda:[0,0]);test=defaultdict(lambda:[0,0]);planned={'train':0,'test':0}
                for w in selected:
                    side='test' if grouping_plan['world_to_fold'][w['world_id']]==fold else 'train'
                    cells=test if side=='test' else train
                    for c in CONDITIONS:
                        row=index[w['world_id']+'.CORE.'+c+'.P4'];planned[side]+=1
                        if row['valid']:cells[c][0]+=1;cells[c][1]+=int(row['semantic_answer']=='B')
                models={}
                for name,interactions in (('main_effects',False),('all_interactions',True)):
                    fitted=fit(train,interactions);first=fitted['status']
                    if first=='not_converged':fitted=fit(train,interactions,max_iter=10000)
                    models[name]=dict(fit=fitted,first_2000_iteration_status=first,test=evaluate(test,fitted,interactions))
                fold_results.append(dict(fold=fold,planned=planned,valid={'train':sum(v[0] for v in train.values()),'test':sum(v[0] for v in test.values())},models=models))
            complete=all(f['models'][name]['test']['log_loss'] is not None for f in fold_results for name in ('main_effects','all_interactions'))
            pooled={}
            if complete:
                for name in ('main_effects','all_interactions'):
                    tests=[f['models'][name]['test'] for f in fold_results];n=sum(t['n'] for t in tests)
                    pooled[name]={metric:sum(t[metric]*t['n'] for t in tests)/n for metric in ('log_loss','Brier')}
            results[subset+'.'+grouping]=dict(status='complete' if complete else 'not_estimable_all_folds_required',folds=fold_results,pooled_test_metrics=pooled)
    return dict(comparisons=results,regularization_C=1.,feature_encoding='R,Q,I at +/-0.5; full pairwise/triple products',
        objective='Sum binary negative log likelihood plus 0.5*sum(nonintercept coefficient squared); intercept unpenalized.',
        solver='Damped Newton, gradient infinity norm <=1e-8, 2000 iterations then 10000 on nonconvergence; no feature or penalty change.',
        interpretation='Held-out behavioral prediction only. Single-class training folds are not estimable under an unpenalized intercept; no rescue profile is silently added.')
