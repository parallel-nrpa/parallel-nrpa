# Nested Deep Learning

## Running experiments

Use `launcher.py`.

### Local run (level 4 NRPA on 4 cores).

```
python3 launcher.py --iterations 100 --atomic_levels 2 --parallel_levels 2 --cores 4 --seed 17
```

### Prometheus run (level 5 NRPA on 96 cores).

```
module load plgrid/tools/python/3.6.5
source envs/nn-nrpa/bin/activate
cd nn-nrpa

python3 launcher.py --pro --iterations 100 --atomic_levels 3 --parallel_levels 2 --cores 96 --seed 17
```

## Prometheus Environment

Virtual environment initialization on Prometheus.

```
cd ~/amn/
module load plgrid/tools/python/3.6.5
virtualenv -p python3 envs/nn-nrpa
source envs/nn-nrpa/bin/activate
cd nn-nrpa
python3 -m pip install --upgrade pip
module load plgrid/tools/tcltk
module load plgrid/libs/cairo
module load plgrid/libs/glib
module load plgrid/libs/pixman
PKG_CONFIG_PATH=$PKG_CONFIG_PATH:/net/software/local/glib/2.52.3/lib/pkgconfig:/net/software/local/software/pixman/0.32.4/lib/pkgconfig
export PKG_CONFIG_PATH
module load plgrid/libs/libpng
module load plgrid/libs/python-numpy/1.14.2-python-3.6
module load plgrid/tools/impi
python3 -m pip install cython numpy
python3 -m pip install atomic_experiments/
python3 -m pip install -r requirements.txt
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
1. Install required python packages.
```
python3 -m pip install -r requirements.txt
python3 -m pip install atomic_experiments/
```
1. Cythonize `.pyx` files
```
cythonize -i -a nrpa.pyx
cythonize -i -a policy.pyx
```