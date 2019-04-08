#include <random>
#include <chrono>
#include <fstream>
#include <iostream>
#include <vector>

#include "morpiongame.h"
#include "cppnrpa.h"

/*
 * The root object holds the root search position.
 * We use it for performance: copying constructor is much faster for MorpionGame.
 */
const MorpionGame root;

/*
 * Holds the search parameters and results.
 * Global for performance.
 */

std::mt19937_64 generator;

CppNRPAExperimentData *state;

float max(float a, float b)
{
    return a > b ? a : b;
}

float min(float a, float b)
{
    return a > b ? b : a;
}

/*
 * Probability weights table. It stores exp(adaptation weight of m) for each move m.
 */

Weights::Weights()
{
    for (int i = 0; i < MorpionGame::max_goedel_number; i++) {
        w[i] = 0.0f;
    }
}

Weights::~Weights()
{
}

Weights::Weights(float _w[])
{
    memcpy(w, _w, sizeof(w));
}

Weights::Weights(const Weights& _w)
{
    memcpy(w, _w.w, sizeof(w));
}

Weights& Weights::operator=(const Weights& _w) {
    memcpy(w, _w.w, sizeof(w));
    return *this;
}

float& Weights::operator[](int i) {
    return w[i];
}

const float& Weights::operator[](int i) const {
    return w[i];
}

// Probability weights adaptation. Standard way (gradient ascent move by move).
void Weights::adapt(const MorpionGame::Sequence &l)
{
    Weights orig(*this);
    MorpionGame simulation(root);

    float W;

    for (unsigned int i = 0; i < l.length; i++) {
        const MorpionGame::Move &m = l.mv[i];

        float smax = -1000000000.0f;
        float smin =  1000000000.0f;

        for (unsigned int i = 0; i < simulation.Moves().length; i++) {
            smax = max(smax,orig[MorpionGame::goedel_number(simulation.Moves().mv[i])]);
            smin = min(smin,orig[MorpionGame::goedel_number(simulation.Moves().mv[i])]);
        }

        float s = (smax + smin) / 2.0f;

        if (smax - s > 5.0f) {
            s = smax - 5.0f;
        }

//            std::cout << "MAX1 " << s << std::endl;

        W = 0.0f;
        for (unsigned int j = 0; j < simulation.Moves().length; j++) {
            W += exp(orig[MorpionGame::goedel_number(simulation.Moves().mv[j])] - s);
        }
//            std::cout << "W " << W << std::endl;

        if (W > 2e10) {
            std::cout << "SMAX " << smax << " SMIN " << smin << " s " << s << std::endl;

            for (unsigned int j = 0; j < simulation.Moves().length; j++) {
                std::cout << orig[MorpionGame::goedel_number(simulation.Moves().mv[j])] << " ";
            }
            std::cout << std::endl;
            for (unsigned int j = 0; j < simulation.Moves().length; j++) {
                std::cout << orig[MorpionGame::goedel_number(simulation.Moves().mv[j])] - s << " ";
            }
            std::cout << std::endl;

            exit(1);
        }

        for (unsigned int j = 0; j < simulation.Moves().length; j++) {
            if (orig[MorpionGame::goedel_number(simulation.Moves().mv[j])] > 2e-10) {
                w[MorpionGame::goedel_number(simulation.Moves().mv[j])] -= alpha *
                        exp(orig[MorpionGame::goedel_number(simulation.Moves().mv[j])] - s) / W;
            }
        }
        w[MorpionGame::goedel_number(m)] += alpha;

        s = -1000000000.0f;
        for (unsigned int j = 0; j < simulation.Moves().length; j++) {
            s = max(s,orig[MorpionGame::goedel_number(simulation.Moves().mv[j])]);
        }
        s = s - 10.0f;
//            std::cout << "MAX2" << s << std::endl;

        simulation.MakeMove(m);
    }
}


/*
 * Single playout given probability weight table. Result is stored in passed sequence.
 */

void simulate(const Weights &w, MorpionGame::Sequence &l)
{
	l.init();

	MorpionGame simulation(root);

	while(simulation.Moves().length > 0) {
        // max of log-weights
		float smax = -1000000000.0f;
		float smin =  1000000000.0f;

        for (unsigned int i = 0; i < simulation.Moves().length; i++) {
            smax = max(smax,w[MorpionGame::goedel_number(simulation.Moves().mv[i])]);
            smin = min(smin,w[MorpionGame::goedel_number(simulation.Moves().mv[i])]);
       	}

       	float s = (smax + smin) / 2.0f;

        if (smax - s > 10.0f) {
            s = smax - 10.0f;
        }

        // sum of adjusted exp-weights
        float W = 0.0f;
        for (unsigned int i = 0; i < simulation.Moves().length; i++) {
            W += exp(w[MorpionGame::goedel_number(simulation.Moves().mv[i])] - s);
       	}

	 	std::uniform_real_distribution<> dis(0.0, W);
        float r = dis(generator);

		float t = 0.0f;

		MorpionGame::Move chosen = simulation.Moves().mv[simulation.Moves().length-1]; // sometimes r would be greater than W!

        for (unsigned int i = 0; i < simulation.Moves().length; i++) {
           	t += exp(w[MorpionGame::goedel_number(simulation.Moves().mv[i])] - s);
			if (t >= r) {
				chosen = simulation.Moves().mv[i]; break;
			}
       	}

		l.mv[l.length++] = chosen;
		simulation.MakeMove(chosen);
	}

	state -> moves += l.length;
	state -> sequences++;
}

/*
 * NRPA
 */

void nrpa(int level, Weights &w, MorpionGame::Sequence &l)
{
	Weights wc(w);
	MorpionGame::Sequence nl;

	for (int i = 0; i < state->iterations; i++) {
		nl.init();

		if (level == 1) {
			simulate(wc, nl);	// replaces level 0 call
		} else {
			nrpa(level - 1, wc, nl);
		}

		if (nl.length >= l.length) {
			l = nl;
		}

    	wc.adapt(l);
	}
}

/*
 * NRPA experiment class.
 */

CppNRPA::CppNRPA() { }

CppNRPA::~CppNRPA() { }

void CppNRPA::run(CppNRPAExperimentData &_state) {
    state = &_state;

    state -> best_sequence.clear();
    state -> histogram.clear();
    state -> histogram.resize(MorpionGame::Sequence::getBound(), 0);
    state -> moves = 0;
    state -> sequences = 0;
    state -> time_us = 0;

    generator.seed(state -> random_seed);

    std::chrono::steady_clock::time_point computation_begin;
    std::chrono::steady_clock::time_point computation_end;

    computation_begin = std::chrono::steady_clock::now();

    MorpionGame::Sequence l;

    for (int i = 0; i < state->batch_size; i++) {
        l.init();
        Weights w(state -> weights);

        if (state -> levels == 0) {
            simulate(w, l);
        } else {
            nrpa(state -> levels, w, l);
        }

        if (l.length > state -> best_sequence.size()) {
            state -> best_sequence.clear();
            for (unsigned int i = 0; i < l.length; i++) {
                state -> best_sequence.push_back(l.mv[i].pythonize());
            }
        }

        state -> histogram[l.length]++;
    }

    computation_end = std::chrono::steady_clock::now();

    state->time_us = std::chrono::duration_cast<std::chrono::microseconds>(computation_end -
                      computation_begin).count();
}

MorpionGame::Sequence cythonize(std::vector<int> seq)
{
    MorpionGame::Sequence s;
    s.init();

    for (int pythonized: seq) {
        s.mv[s.length++] = MorpionGame::Move(pythonized);
    }

    return s;
}
