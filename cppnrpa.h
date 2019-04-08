#ifndef CPPNRPA_H
#define CPPNRPA_H
class Weights
{
public:
	float w[MorpionGame::max_goedel_number];
    float alpha = 1.0; // FIXME

	Weights();
	~Weights();
    Weights(float _w[]);
	Weights(const Weights& _w);
	Weights& operator=(const Weights& _w);
	float& operator[](int i);
	const float& operator[](int i) const;
    void adapt(const MorpionGame::Sequence &l);
};

MorpionGame::Sequence cythonize(std::vector<int> seq);

struct CppNRPAExperimentData {
    /*
     * Search parameters.
     */
    int batch_size;             // Batch size
    long long int random_seed;  // RNG seed
	unsigned int levels;    	// number of levels
	int iterations;			    // number of iterations at every level
	float alpha;				// alpha value
	MorpionGame::Variant v;		// 5T or 5D
    float weights[MorpionGame::max_goedel_number];

    /*
     * Search results.
     */
	std::vector<int> best_sequence;
    std::vector<long long int> histogram;
    long long int moves;
    long long int sequences;
    long long int time_us;
};

class CppNRPA {
public:
    CppNRPA();
    ~CppNRPA();

    void run(CppNRPAExperimentData &_state);
};

#endif /* CPPNRPA_H */
