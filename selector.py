"""
Heuristics for selecting a pending rollout for computation.
"""

import rollout

class Selector:
    def __init__(self):
        pass

    def select(self, rollout):
        raise NotImplementedError

class DFSSelector(Selector):
    def select(self, rout):
        if rout.is_atomic():
            if rout.state == rollout.Rollout.State.pending:
                return rout
            else:
                return None

        for child in rout.active_pool:
            found = self.select(child)

            if found is not None:
                return found

        return None

class ProbabilitySelector(Selector):
    @staticmethod
    def sequence_change_probability(length):
        if length >= 150:
            return 0.1
        if length >= 140:
            return 0.2
        if length >= 120:
            return 0.3
        if length >= 80:
            return 0.5
        if length >= 64:
            return 0.95
        return 1.0

    @staticmethod
    def policy_change_probability(node, parent_change_probability):
        if node.state == rollout.Rollout.State.completed:
            return (None, 1.0)

        my_prob = 1.0 - parent_change_probability

        sibling = node.sibling
        while sibling is not None:
            if sibling.state != rollout.Rollout.State.completed:
                my_prob = my_prob * (1.0 - ProbabilitySelector.sequence_change_probability(len(node.adapt_sequence)))
            sibling = sibling.sibling

        if node.is_atomic():
            if node.state == rollout.Rollout.State.pending:
                return (node, 1.0 - my_prob)
            else:
                return (None, 1.0)
        else:
            best_prob = 1.0
            best_child = None
            for child in node.active_pool:
                child_node, child_prob = ProbabilitySelector.policy_change_probability(child, 1.0-my_prob)

                if child_prob < best_prob:
                    best_prob = child_prob
                    best_child = child_node

            return (best_child, best_prob)

    def select(self, rout):
        node, prob = ProbabilitySelector.policy_change_probability(rout, 0.0)

        if node is None:
            print("Selector found no node.")

        return node