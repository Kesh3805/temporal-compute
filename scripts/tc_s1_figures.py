"""Neutral static TC-S1 figures; scientific results come from frozen analysis."""
import argparse
import gzip
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from tc_s1_generate import config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    args = parser.parse_args()
    root = args.results
    out = root/'figures'
    out.mkdir(exist_ok=True)
    cfg = config()
    aggregate = json.loads((root/'aggregate.json').read_text())
    paired = json.loads((root/'paired-comparisons.json').read_text())
    sensitivity = json.loads((root/'sensitivity.json').read_text())
    oracle = json.loads((root/'oracle.json').read_text())
    policies = cfg['schedulers']
    labels = ['FIFO','Fixed\npriority','EDF','EDF +\npriority','Temporal\nutility','Utility\ndensity']
    colors = ['#757575','#a0a0a0','#9a7960','#9b829d','#31688e','#33877e']
    plt.rcParams.update({'font.size':10,'svg.hashsalt':'tc-s1','axes.spines.top':False,'axes.spines.right':False})

    def save(fig,name):
        fig.tight_layout()
        fig.savefig(out/(name+'.png'),dpi=160,metadata={'Software':'Temporal Compute'})
        fig.savefig(out/(name+'.svg'),metadata={'Date':None,'Creator':None})
        plt.close(fig)

    fig,ax = plt.subplots(figsize=(9,4.5))
    values = [aggregate['policies'][p]['normalized_utility'] for p in policies]
    ax.bar(labels,values,color=colors)
    ax.set_ylim(0,1)
    ax.set_ylabel('Corpus realized / base utility (not oracle capture)')
    ax.set_title('TC-S1: frozen fictional EO corpus, 200 instances')
    for i,v in enumerate(values):
        ax.text(i,v+.015,f'{v:.1%}',ha='center')
    save(fig,'corpus-utility')

    rows = []
    with gzip.open(root/'corpus/metrics.jsonl.gz','rt') as file:
        for line in file:
            row = json.loads(line)
            if row['profile']=='primary':
                rows.append(row)
    fig,ax = plt.subplots(figsize=(9,4.5))
    for i,p in enumerate(policies):
        values = sorted(r['metrics']['normalized_utility'] for r in rows if r['scheduler']==p)
        ax.plot(values,np.arange(1,len(values)+1)/len(values),label=labels[i].replace('\n',' '),color=colors[i])
    ax.set(xlim=(0,1),ylim=(0,1),xlabel='Per-instance realized / base utility',ylabel='Empirical cumulative fraction',title='Utility distribution: every primary instance')
    ax.legend(fontsize=8)
    save(fig,'utility-distribution')

    fig,axes = plt.subplots(2,2,figsize=(10,7),sharex=True,sharey=True)
    maximum = max(abs(d) for b in cfg['baselines'] for d in paired[b]['paired_deltas'])
    bins = np.linspace(-maximum,maximum,25)
    for ax,b in zip(axes.flat,cfg['baselines']):
        ax.hist(paired[b]['paired_deltas'],bins=bins,color='#31688e',edgecolor='white')
        ax.axvline(0,color='black',linewidth=1)
        ax.set_title('Temporal utility minus '+b)
        ax.set_ylabel('Instances')
        ax.set_xlabel('Paired utility delta (points)')
    save(fig,'paired-deltas')

    fig,ax = plt.subplots(figsize=(10,5))
    names = list(cfg['load_regimes'])
    x = np.arange(len(names))
    for i,p in enumerate(policies):
        values = [aggregate['groups']['load_regime'][n][p]['normalized_utility'] for n in names]
        ax.bar(x+(i-2.5)*.13,values,width=.13,label=labels[i].replace('\n',' '),color=colors[i])
    ax.set_xticks(x,names)
    ax.set_ylim(0,1)
    ax.set_ylabel('Group realized / base utility')
    ax.set_title('Utility by nominal offered-load regime')
    ax.legend(fontsize=8,ncols=3,loc='lower center',bbox_to_anchor=(.5,1.12))
    save(fig,'load-regimes')

    fig,ax = plt.subplots(figsize=(10,5))
    names = list(cfg['mission_mixes'])
    x = np.arange(len(names))
    for i,p in enumerate(policies):
        ax.bar(x+(i-2.5)*.13,[aggregate['groups']['mission_mix'][n][p]['normalized_utility'] for n in names],width=.13,label=labels[i].replace('\n',' '),color=colors[i])
    ax.set_xticks(x,names)
    ax.set_ylim(0,1)
    ax.set_ylabel('Group realized / base utility')
    ax.set_title('Utility by assumed mission mix')
    ax.legend(fontsize=8,ncols=3,loc='lower center',bbox_to_anchor=(.5,1.12))
    save(fig,'mission-mixes')

    fig,ax = plt.subplots(figsize=(9,5))
    names = [n for n in cfg['class_order'] if cfg['classes'][n]['critical']]
    x = np.arange(len(names))
    for i,p in enumerate(policies):
        ax.bar(x+(i-2.5)*.13,[aggregate['policies'][p]['classes'][n]['critical_success_rate'] for n in names],width=.13,label=labels[i].replace('\n',' '),color=colors[i])
    ax.set_xticks(x,[n.replace('_',' ').title() for n in names])
    ax.set_ylim(0,1)
    ax.set_ylabel('Critical-job success rate (>= half base utility)')
    ax.set_title('Critical classes reported separately')
    ax.legend(fontsize=8,ncols=3,loc='lower center',bbox_to_anchor=(.5,1.12))
    save(fig,'critical-success')

    fig,ax = plt.subplots(figsize=(9,5))
    matrix = [[aggregate['policies'][p]['classes'][n]['utility_retained'] for p in policies] for n in cfg['class_order']]
    image = ax.imshow(matrix,vmin=0,vmax=1,cmap='cividis',aspect='auto')
    ax.set_xticks(range(6),labels)
    ax.set_yticks(range(6),[n.replace('_',' ').title() for n in cfg['class_order']])
    fig.colorbar(image,ax=ax,label='Class realized / base utility')
    ax.set_title('Retained value by class')
    save(fig,'class-retention')

    names = list(cfg['sensitivity'])
    matrix = []
    for name in names:
        a = sensitivity[name]['aggregates']
        best = max(a[b]['total_utility'] for b in cfg['baselines'])
        matrix.append([(a[p]['total_utility']-best)/best for p in policies])
    maximum = max(abs(v) for row in matrix for v in row)
    fig,ax = plt.subplots(figsize=(10,8))
    image = ax.imshow(matrix,cmap='RdBu',vmin=-maximum,vmax=maximum,aspect='auto')
    ax.set_xticks(range(6),labels)
    ax.set_yticks(range(len(names)),names)
    for i,row in enumerate(matrix):
        for j,value in enumerate(row):
            ax.text(j,i,f'{value:+.1%}',ha='center',va='center',fontsize=8,color='white' if abs(value)>.55*maximum else 'black')
    fig.colorbar(image,ax=ax,label='Relative total gain over best conventional in same variant')
    ax.set_title('All preregistered one-factor sensitivities')
    save(fig,'sensitivity')

    fig,ax = plt.subplots(figsize=(9,4.5))
    ax.bar(labels,[oracle['summary'][p]['corpus_capture'] for p in policies],color=colors)
    ax.set_ylim(0,1)
    ax.set_ylabel('Sum(policy utility) / sum(exact oracle utility)')
    ax.set_title('40 derived nine-job problems — not the full primary corpus')
    save(fig,'oracle-capture')
    print('Nine static figures written in PNG and SVG:',out)


if __name__=='__main__':
    main()
