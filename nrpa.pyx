# distutils: language = c++
# distutils: sources = cppnrpa.cpp morpiongame.cpp
# distutils: extra_compile_args=["-std=c++14"]

from libcpp.vector cimport vector
import numpy as np

cdef extern from "morpiongame.h" namespace "MorpionGame":
    cdef enum Variant: T5, D5

cdef extern from "morpiongame.h" namespace "MorpionGame::Sequence":
    cdef const int bound;

cdef extern from "morpiongame.h" namespace "MorpionGame":
    cdef const int max_goedel_number

cdef extern from "morpiongame.h" namespace "MorpionGame":
    cdef struct Move:
        int pos;
        int dir;

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
    cdef struct CppNRPAExperimentData:
        int batch_size;
        long long int random_seed;
        unsigned int levels;
        int iterations;
        float alpha;
        int v;
        float weights[max_goedel_number]

        vector[int] best_sequence;
        vector[long long int] histogram;
        long long int moves;
        long long int sequences;
        long long int time_us;

cdef extern from "cppnrpa.h":
    cdef cppclass CppNRPA:
        void run(CppNRPAExperimentData &);

cdef class NRPA:
    cdef CppNRPA nrpa
    cdef CppNRPAExperimentData experiment_data

    def set_payload(self, payload):
        self.experiment_data.weights = payload['weights'].get_weights()

    def run(self, payload):
        self.experiment_data.batch_size = payload['batch_size']
        self.experiment_data.levels = payload['levels']
        self.experiment_data.iterations = payload['iterations']
        self.experiment_data.alpha = payload['alpha']
        self.experiment_data.random_seed = payload['random_seed']
        self.experiment_data.v = T5;
#        self.experiment_data.weights = payload['weights'].get_weights()
        self.set_payload(payload)

        self.nrpa.run(self.experiment_data)

        result = dict()

        result['batch_size'] = self.experiment_data.batch_size
        result['random_seed'] = self.experiment_data.random_seed
        result['levels'] = self.experiment_data.levels
        result['iterations'] = self.experiment_data.iterations
        result['alpha'] = self.experiment_data.alpha
        result['v'] = self.experiment_data.v

        result['weights'] = np.array(self.experiment_data.weights, copy=True)
        result['best_sequence'] = self.experiment_data.best_sequence
        result['histogram'] = self.experiment_data.histogram
        result['moves'] = self.experiment_data.moves
        result['sequences'] = self.experiment_data.sequences
        result['time_us'] = self.experiment_data.time_us

        return result
