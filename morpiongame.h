#ifndef __MORPION_H__
#define __MORPION_H__
#include <vector>
#include <string>
#include <iostream>
#include <string.h>

class MorpionGame
{
public:
	enum Variant { T5 = 0, D5 = 1 };

	int variant = T5;

    static const int SIZE = 40;

	// Invalidate moves that are outside of the octagonal board
	void clipBoard(int o[8])
	{
		for (Position p = 0; p < ARRAY_SIZE; p++) {
			for (Direction d = 0; d < DIRS; d++) {
				if (!LineInsideBoard(p,d,o)) {
					IncDotCount(p,d,LINE);
				}
			}
		}
	}

	// Invalidate asymmetric moves
	void clipAsymmetric()
	{
		IncDotCount(ReferencePoint() + PositionOfCoords(2,1), 3, LINE);
		IncDotCount(ReferencePoint() + PositionOfCoords(3,0), 3, LINE);
		IncDotCount(ReferencePoint() + PositionOfCoords(4,-1), 3, LINE);
		IncDotCount(ReferencePoint() + PositionOfCoords(5,-2), 3, LINE);

		IncDotCount(ReferencePoint() + PositionOfCoords(1,1), 1, LINE);
		IncDotCount(ReferencePoint() + PositionOfCoords(0,0), 1, LINE);
		IncDotCount(ReferencePoint() + PositionOfCoords(-1,-1), 1, LINE);
		IncDotCount(ReferencePoint() + PositionOfCoords(-2,-2), 1, LINE);
	}

    typedef int Direction;
    typedef int Position;

    Position PositionOfCoords(int x, int y) const;
    void CoordsOfPosition(Position p, int & x, int & y) const;

    struct Move
    {
        Position pos;
        Direction dir;
        Move() {}
        Move(Position pos, Direction dir) : pos(pos), dir(dir) {}
        int pythonize() const {
            return pos * 4 + dir;
        }
        Move(int pythonized) {
            pos = pythonized / 4;
            dir = pythonized % 4;
        }
    };

	class Sequence {
		static const int bound = 200;   // Warning: this number is hardcoded in nrpa.pyx

	public:
		unsigned int length;
		Move mv[bound];

        static const int getBound() {
            return bound;
        }
		Sequence() {
			init();
		}

		void init() {
			length = 0;
		}

		Sequence& operator=(const Sequence& s) {
			length = s.length;
			memcpy(mv, s.mv, length * sizeof(Move));
			return *this;
		}
	};

    MorpionGame();
	const Sequence& Moves() const;
    void MakeMove(Move move);

	MorpionGame(const MorpionGame& g)
	{
		variant = g.variant;
		memcpy(has_dot, g.has_dot, sizeof(has_dot));
		memcpy(dots_count, g.dots_count, sizeof(dots_count));
		memcpy(move_index, g.move_index, sizeof(move_index));
		legal_moves = g.legal_moves;
	}

protected:
    /*  o-
     * /|\ */
    
    enum { RIGHT = 0, DOWN = 2, LEFT = 4, UP = 6 };
    
    static const int DIRS = 4;
    static const int ARRAY_SIZE = SIZE * SIZE;
    static const int LINE = 5; // in number of dots
    static const int dir[DIRS];

    bool has_dot[ARRAY_SIZE];
    int dots_count[ARRAY_SIZE][DIRS];
    int move_index[ARRAY_SIZE][DIRS];
    Sequence legal_moves;
    
    bool CanMove(Position pos, Direction d) const
    {
        return dots_count[pos][d] == LINE - 1;
    }

    void IncDotCount(Position pos, Direction d, int count);
    void PutDot(Position pos, int count);

    int ShiftFromDir(int d) { return d < DIRS ? dir[d] : -dir[d - DIRS]; }

    Position ReferencePoint() const;
    
    int CharDirToIntDir(char c);
    char IntDirToCharDir(int dir);

	// Directions:
	//   N NE E SE S SW W NW
    //   0 1  2 3  4 5  6 7

	const int nx[8] = { 0, 2, 2, 2,  0,  -2, -2, -2 };
	const int ny[8] = { 2, 2, 0, -2, -2, -2, 0,  2  };

    int DistanceFromOrigin(Position p, int dir)
    {
		int px, py; 
		CoordsOfPosition(p, px, py);

		int rx, ry;
		CoordsOfPosition(ReferencePoint(), rx, ry);

		return (2*(px - rx) - 3) * nx[dir] + (2*(py - ry) - 3) * ny[dir];
    }

	bool InsideBoard(Position p, int octagon[8])
	{
		for (int dir = 0; dir < 8; dir++) {
			if (octagon[dir] == 0) continue;
			if (DistanceFromOrigin(p, dir) > octagon[dir]) return false;
		}
		return true;
	}

	bool LineInsideBoard(Position p, Direction d, int o[8])
	{
		for (int i = 0; i < LINE; i++) {
			if (!has_dot[p + dir[d] * i] && !InsideBoard(p + dir[d] * i,o)) return false;
		}
		return true;
	}

public:
	Move symmetric(Move m) const
	{
		return Move(-m.pos + 2 * ReferencePoint() + PositionOfCoords(3,3) - 4 * dir[m.dir], m.dir);
	}

    static const int max_goedel_number = DIRS * ARRAY_SIZE;
    static inline int goedel_number(const Move &m)
    {
        return m.dir * ARRAY_SIZE + m.pos;
    }

	void print(int o[8])
	{
		for (int y = 0; y < SIZE; y++) {
			for (int x = 0; x < SIZE; x++) {
				if (PositionOfCoords(x,y) == ReferencePoint()) {
					std::cout << "R";
				} else if (has_dot[PositionOfCoords(x,y)]) {
					std::cout << "*";
				} else if (InsideBoard(PositionOfCoords(x,y),o)) {
					std::cout << ".";
				} else {
					std::cout << " ";
				}
			}
			std::cout << std::endl;
		}
	}
};

inline const MorpionGame::Sequence& MorpionGame::Moves() const
{
    return legal_moves;
}

inline MorpionGame::Position MorpionGame::PositionOfCoords(int x, int y) const
{
    return x + y * SIZE;
}

inline void MorpionGame::CoordsOfPosition(Position p, int & x, int & y) const
{
    x = p % SIZE;
    y = p / SIZE;
}

std::ostream& operator<<(std::ostream& os, MorpionGame::Variant v);
std::ostream& operator<<(std::ostream& os, MorpionGame::Sequence v);

#endif

