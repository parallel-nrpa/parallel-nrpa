# distutils: language = c++
# distutils: sources = cppnrpa.cpp morpiongame.cpp
# distutils: extra_compile_args=["-std=c++14"]

from libcpp.vector cimport vector
import numpy as np

cdef class Policy:
    """Abstract base class."""

    def simulate(self):
        raise NotImplementedError


cdef extern from "morpiongame.h" namespace "MorpionGame":
    cdef enum Variant: T5, D5

cdef extern from "morpiongame.h" namespace "MorpionGame":
    cdef const int max_goedel_number

cdef extern from "morpiongame.h" namespace "MorpionGame":
    cdef struct Move:
        int pos;
        int dir;

cdef extern from "morpiongame.h" namespace "MorpionGame::Sequence":
    cdef const int bound;

cdef extern from "morpiongame.h" namespace "MorpionGame":
    cdef struct Sequence:
        unsigned int length;
        Move mv[bound];

cdef extern from "cppnrpa.h":
    cdef cppclass Weights:
        float[max_goedel_number] w

        Weights();
        Weights(const Weights & _w);
        Weights & operator = (const Weights & _w);
        void adapt(const Sequence & l);

cdef extern from "cppnrpa.h":
    cdef Sequence cythonize(vector[int] seq);


cdef class WeightPolicy(Policy):
    cdef Weights weights

    def adapt(self, sequence):
        self.weights.adapt(cythonize(sequence))

    def __repr__(self):
        return str(self.weights.w)

    def __reduce__(self):
        d=dict()
        d['weights'] = np.asarray(self.weights.w)
        return (WeightPolicy, (d['weights'], ), d)

    def __setstate__(self, d):
        self.weights.w = d['weights']

    def get_weights(self):
        return self.weights.w

    def __eq__(self, p):
        return str(self) == str(p)
