#!/usr/bin/env python3

"""
Experiment launcher.
"""

import argparse
import logging
from termcolor import colored
import tempfile
import os

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()

parser.add_argument('--pro', dest='prometheus', action='store_true')
parser.add_argument('--cores', type=int, default=5)
parser.set_defaults(prometheus=False)

parser.add_argument('--seed', type=int, default=1)
parser.add_argument('--iterations', type=int, default=100)
parser.add_argument('--parallel_levels', type=int, default=2)
parser.add_argument('--atomic_levels', type=int, default=2)
parser.add_argument('--alpha', type=float, default=1.0)

args = parser.parse_args()


def print_param(param, value):
    print('{0:>15}: {1}'.format(param, colored(value, attrs=['bold'])))


print(colored('Parallel NRPA Experiment Launcher', 'yellow', attrs=['bold']))
print('')
print_param('Environment', 'prometheus' if args.prometheus else 'local')

print_param('Cores', args.cores)

if args.prometheus:
    nodes = (args.cores + 23) // 24
    memory = '32GB'
    time = '1200:00'

    print_param('Nodes', nodes)
    print_param('Memory', memory)
    print_param('Time', time)

experiment_dir = tempfile.mkdtemp(dir='experiments/')

print_param('Directory', experiment_dir)
print('')
print_param('Random seed', args.seed)
print_param('Iterations', args.iterations)
print_param('Parallel levels', args.parallel_levels)
print_param('Atomic levels', args.atomic_levels)
print_param('Alpha', args.alpha)
print('')

saved_dir = os.getcwd()
os.chdir(experiment_dir)

if args.prometheus:
    slurm = """\
#!/bin/env bash
#SBATCH --nodes={0}
#SBATCH --ntasks-per-node=24
#SBATCH --cpus-per-task=1
#SBATCH --time={1}
#SBATCH -p plgrid
#SBATCH --mem={2}

# https://software.intel.com/en-us/forums/intel-clusters-and-hpc-technology/topic/289963
# added after https://app.neptune.ml/-/dashboard/experiment/830c720b-49ef-4d51-8801-cc1611bcfd83
# TODO: test if this is really needed
export I_MPI_USE_DYNAMIC_CONNECTIONS=0

module load plgrid/tools/python/3.6.5
module load plgrid/tools/tcltk

source ~/amn/envs/nn-nrpa/bin/activate

module load plgrid/libs/cairo
module load plgrid/libs/glib
module load plgrid/libs/pixman
module load plgrid/libs/libpng
module load plgrid/libs/python-numpy/1.14.2-python-3.6

# cp token ~/.neptune/tokens/

neptune run --config experiment.yaml
    """.format(nodes, time, memory)
    print(slurm, file=open('experiment.slurm', 'wt'))

    yaml = """\
project: nn-nrpa
name: Parallel NRPA
description: Parallel NRPA
open-webbrowser: false

parameters:
  cores: &cores "{0}"
  parallel_levels: {1}
  atomic_levels: {2}
  iterations: {3}
  alpha: {4}
  seed: {5}

command: [ srun, --mpi=pmi2, -n, *cores, {6}/parallel_nrpa.py ]

exclude: [ '*' ]
    """.format(args.cores, args.parallel_levels, args.atomic_levels, args.iterations, args.alpha,
                   args.seed, saved_dir)
    print(yaml, file=open('experiment.yaml', 'wt'))

    os.system('sbatch experiment.slurm')

    print(colored('Scheduled {0}/experiment.slurm for execution.'.format(experiment_dir), attrs=['bold']))
else:
    yaml = """\
project: nn-nrpa
name: Parallel NRPA
description: Parallel NRPA
open-webbrowser: false

parameters:
  cores: &cores "{0}"
  parallel_levels: {1}
  atomic_levels: {2}
  iterations: {3}
  alpha: {4}
  seed: {5}
  
command: [ mpirun, -n, *cores, {6}/parallel_nrpa.py ]

exclude: [ '*' ]
    """.format(args.cores, args.parallel_levels, args.atomic_levels, args.iterations, args.alpha,
               args.seed, saved_dir)

    print(yaml, file=open('experiment.yaml', 'wt'))

    os.system('neptune run --config experiment.yaml'.format(experiment_dir))
os.chdir(saved_dir)
