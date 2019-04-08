# Parallel Nested Rollout Policy Adaptation

The code that can be used to replicate experiments described in `Parallel Nested Rollout Policy Adaptation` paper.

## Running experiments

Use `launcher.py`. You need to log into a Neptune account first with `neptune account login` from the command line.

### Local run (level 4 NRPA on 4 cores).

```
python3 launcher.py --iterations 100 --atomic_levels 2 --parallel_levels 2 --cores 4 --seed 17
```

## Local Development Environment

### Non-python requirements

Ubuntu packages.

* `libgirepository1.0-dev` - for `Gtk`
* `mpi-default-dev` - for `mpi4py`
* `python3-testresources` - for `neptune-cli`

### Using Ubuntu and command line

1. Create virtualenv and activate it.
```
python3 -m virtualenv -p python3 <dir>
cd <dir>
source bin/activate
```
2. Install required python packages.
```
python3 -m pip install -r requirements.txt
python3 -m pip install atomic_experiments/
```
3. Cythonize `.pyx` files
```
cythonize -i -a nrpa.pyx
cythonize -i -a policy.pyx
```
4. Create `experiments/` dicrectory
```
mkdir experiments/
```
