#include <vector>
#include <string>
#include <iostream>
#include <string.h>

#include "morpiongame.h"

using namespace std;

const int MorpionGame::dir[MorpionGame::DIRS] = {1, SIZE + 1, SIZE, SIZE - 1};

MorpionGame::MorpionGame()
{
    memset(has_dot, 0, sizeof(has_dot));
    memset(dots_count, 0, sizeof(dots_count));
    memset(move_index, 0, sizeof(move_index));
    static const int cross[] = {
        RIGHT, UP, RIGHT, DOWN, RIGHT, DOWN, LEFT, DOWN, LEFT, UP, LEFT, UP
    };
    static const int ARMLEN = LINE - 2;
    Position p =
        PositionOfCoords((SIZE - 3 * ARMLEN) / 2,
                         (SIZE - ARMLEN) / 2);
    for (int i = 0; i < 12; i++)
    {
        int d = ShiftFromDir(cross[i]);
        for (int j = 0; j < ARMLEN; j++)
        {
            p += d;
            PutDot(p, 1);
        }
    }
}

void MorpionGame::IncDotCount(Position pos, Direction d, int count)
{
    if (CanMove(pos, d))
    {
        int idx = move_index[pos][d];
        Move& back = legal_moves.mv[legal_moves.length-1];
        move_index[back.pos][back.dir] = idx;
        legal_moves.mv[idx] = back;
        legal_moves.length--;
    }
    dots_count[pos][d] += count;
    if (CanMove(pos, d))
    {
        move_index[pos][d] = legal_moves.length;
		legal_moves.mv[legal_moves.length].dir = d;
        legal_moves.mv[legal_moves.length++].pos = pos;
    }
}

void MorpionGame::PutDot(Position pos, int count)
{
    has_dot[pos] = count > 0;
    for (Direction d = 0; d < DIRS; d++)
    {
        Position p = pos;
        for (int i = 0; i < LINE; i++)
        {
            IncDotCount(p, d, count);
            p -= dir[d];
        }
    }
}

void MorpionGame::MakeMove(Move move)
{
    /* Block moves overlaping with segments added by the move */
    for (int i = -(LINE - 2 + variant); i <= LINE - 2 + variant; i++)
        IncDotCount(move.pos + dir[move.dir] * i, move.dir, LINE);
    /* Find dot and put it */
    for (int i = 0; i < LINE; i++)
    {
        Position p = move.pos + dir[move.dir] * i;
        if (!has_dot[p])
        {
            PutDot(p, 1); break;
        }
    }
}

MorpionGame::Position MorpionGame::ReferencePoint() const
//     XXXX
//     X  X
//     X  X
//  XXXR  XXXX
//  X        x
//  X        x
//  XXXX  XXXX
//     X  X
//     X  X
//     XXXX
//
//     R - reference point
{
    const int ARMLEN = LINE - 2;
    const int MIDDLE = (SIZE - ARMLEN) / 2;
    return PositionOfCoords(MIDDLE, MIDDLE);
}

int MorpionGame::CharDirToIntDir(char c)
{
    switch (c) {
        case '-':
            return 0;
        case '\\':
            return 1;
        case '|':
            return 2;
        case '/':
            return 3;
        default:
            return -1;
    };
}

char MorpionGame::IntDirToCharDir(int dir)
{
    static const char mapping[] = {'-', '\\', '|', '/'};
    return mapping[dir];
}


std::ostream& operator<<(std::ostream& os, MorpionGame::Variant v)
{
    switch (v) {
        case MorpionGame::D5: os << "5D"; break;
        case MorpionGame::T5: os << "5T"; break;
    }
    return os;
}

std::ostream& operator<<(std::ostream& os, MorpionGame::Sequence )
{
	return os;
}
