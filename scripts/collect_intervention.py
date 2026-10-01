"""Apply the fixed 48-test Holm family to three prespecified model analyses."""
import argparse
from pathlib import Path
from epistemic_benchmark.analysis.diagnostics import holm
from epistemic_benchmark.utils.io import compute_only, read, require, write


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,nargs=3,required=True,help='Analyses in order: Qwen3.5-9B, Qwen3.5-27B, Qwen3.6-27B')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();compute_only()
    require(not args.output.exists(),'Choose a new output path')
    require(len({p.resolve() for p in args.inputs})==3,'Three distinct model analyses are required')
    models=('Qwen/Qwen3.5-9B','Qwen/Qwen3.5-27B','Qwen/Qwen3.6-27B')
    values={};records=[]
    for model,path in zip(models,args.inputs):
        analysis=read(path);require(analysis['worlds']==500 and analysis['planned_requests']==50000,'Incomplete analysis inventory')
        primary=[r for r in analysis['comparisons'] if r['primary']]
        require(len(primary)==16,'Primary comparisons changed')
        for row in primary:
            key='|'.join((model,row['subset'],row['comparison'],row['metric']))
            require(key not in values,'Duplicate comparison')
            values[key]=row['centered_bootstrap_p'];records.append(dict(model=model,comparison_key=key,**row))
    require(len(values)==48,'Family size must remain 48')
    adjusted=holm(values,48)
    for row in records:row['holm_p']=adjusted[row['comparison_key']]
    write(args.output,dict(planned_tests=48,comparisons=records))


if __name__=='__main__':main()
